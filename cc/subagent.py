"""Subagent — isolated agent instances with per-model selection and tool filtering."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from cc.config import Config
from cc.llm import LLMClient, Usage
from cc.safety import SafetyChecker
from cc.output import Logger


@dataclass
class SubagentTask:
    prompt: str
    model: str | None = None
    project_dir: str = ""
    tools: list[str] | None = None
    max_iterations: int = 10
    max_output_tokens: int = 50_000
    timeout: int = 120
    system_prompt: str | None = None
    context: list[dict] | None = None


@dataclass
class SubagentResult:
    text: str | None
    model: str
    usage: Usage
    iterations_used: int
    success: bool = True
    error: str | None = None


def run_subagent(task: SubagentTask, plugins=None, parent_config=None) -> SubagentResult:
    """Run an isolated subagent. Returns SubagentResult."""
    from cc.tools import _TOOLS, _SKILL_TOOL_DEF, get_tool_defs, execute_tool
    from cc.agent import _build_system_prompt, _run_loop
    from cc.config import load_config

    model = task.model or (parent_config.model if parent_config else Config().model)

    try:
        # Start from load_config to pick up env vars / yaml (OCI settings etc)
        config = load_config(
            model=model,
            max_iterations=task.max_iterations,
            timeout=task.timeout,
            project_dir=task.project_dir or ".",
        )
        # Inherit OCI settings from parent if available
        if parent_config:
            config.oci_region = parent_config.oci_region
            config.oci_compartment = parent_config.oci_compartment
            config.oci_config_profile = parent_config.oci_config_profile

        llm = LLMClient(config)
        safety = SafetyChecker(project_dir=config.project_dir)
        log = Logger(verbose=False, model=model)

        # Build skill registry from plugins
        skill_registry = {}
        plugin_list = plugins or []
        for plugin in plugin_list:
            skill_registry.update(plugin.skills)

        skill_descriptions = [
            f"{name} — {s.description}" for name, s in skill_registry.items()
        ]

        # Filter tools — always exclude spawn_subagent
        exclude = {"spawn_subagent"}
        if task.tools is not None:
            valid = set(_TOOLS.keys()) - exclude
            requested = set(task.tools) - exclude
            invalid = requested - valid
            if invalid:
                print(f"Warning: unknown tool names ignored: {', '.join(sorted(invalid))}", file=sys.stderr)
            tool_names = requested & valid
            if not tool_names:
                return SubagentResult(
                    text=None, model=model, usage=Usage(), iterations_used=0,
                    success=False, error="No valid tools after filtering",
                )
            tools = [defn for name, (defn, _) in _TOOLS.items() if name in tool_names]
        else:
            tools = get_tool_defs(exclude=list(exclude))

        # Add use_skill tool if skills available
        if skill_descriptions:
            skill_tool = _SKILL_TOOL_DEF.copy()
            desc = skill_tool["function"]["description"]
            desc += "\n\nAvailable skills:\n" + "\n".join(f"- {s}" for s in skill_descriptions)
            skill_tool["function"]["description"] = desc
            tools.append(skill_tool)

        # Build system prompt with plugin context
        system_prompt_text = _build_system_prompt(config, plugin_list, skill_registry)
        if task.system_prompt:
            system_prompt_text += f"\n\n{task.system_prompt}"

        # Build messages
        messages = [{"role": "system", "content": system_prompt_text}]
        if task.context:
            messages.extend(task.context)
        messages.append({"role": "user", "content": task.prompt})

        start_time = time.monotonic()

        loop_result = _run_loop(
            config, llm, log, None, safety, skill_registry,
            messages, tools, start_time,
            0, 0, 0,
            max_output_tokens=task.max_output_tokens,
        )

        return SubagentResult(
            text=loop_result.text,
            model=model,
            usage=Usage(
                input_tokens=loop_result.total_input,
                output_tokens=loop_result.total_output,
                reasoning_tokens=loop_result.total_reasoning,
            ),
            iterations_used=loop_result.iterations_used,
            success=True,
        )

    except Exception as e:
        return SubagentResult(
            text=None,
            model=model,
            usage=Usage(),
            iterations_used=0,
            success=False,
            error=str(e),
        )


def run_subagents_parallel(tasks: list[SubagentTask], plugins=None, parent_config=None) -> list[SubagentResult]:
    """Run multiple subagents concurrently. Always collects all results."""
    max_workers = min(len(tasks), 5)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(run_subagent, task, plugins, parent_config) for task in tasks]
        return [f.result() for f in futures]
