"""Agent loop — the core tool loop that drives task execution."""

import json
import time
from cc.config import Config
from cc.llm import LLMClient, LLMResponse
from cc.safety import SafetyChecker
from cc.tools import get_all_tools, execute_tool
from cc.plugins.loader import PluginInfo
from cc.output import Logger
from cc.stream import StreamEmitter


def _build_system_prompt(config: Config, plugins: list[PluginInfo], skill_registry: dict) -> str:
    parts = [
        "You are litecc, a coding agent that helps with software engineering tasks.",
        f"You can only access files inside the project directory: {config.project_dir}",
        "You cannot delete files or run destructive commands — they will be blocked.",
        "Use tools to explore, read, edit, and run commands. Be concise and focused.",
        "IMPORTANT: You are running non-interactively — there is no user to answer questions.",
        "Never stop to ask the user for input. If data is missing, make a reasonable assumption",
        "(e.g., use ticket creation time as alarm timestamp, use a default namespace),",
        "note your assumption, and continue. Always prefer progress over perfection.",
    ]

    for plugin in plugins:
        if plugin.claude_md:
            parts.append(f"\n## Plugin: {plugin.name}\n{plugin.claude_md}")

    if skill_registry:
        parts.append("\n## Available Skills")
        parts.append("Call use_skill with a skill name to load its instructions.")
        for name, skill in skill_registry.items():
            desc = skill.description[:200] if skill.description else "No description"
            parts.append(f"- **{name}**: {desc}")

    return "\n\n".join(parts)


def _build_content_blocks(response: LLMResponse) -> list[dict]:
    """Build content block array from an LLM response for stream-json."""
    blocks = []
    if response.text:
        blocks.append({"type": "text", "text": response.text})
    if response.tool_calls:
        for tc in response.tool_calls:
            blocks.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
    return blocks


def run_agent(
    prompt: str,
    config: Config,
    llm: LLMClient,
    plugins: list[PluginInfo],
) -> str:
    log = Logger(verbose=config.verbose, model=config.model)
    safety = SafetyChecker(project_dir=config.project_dir)

    stream = None
    if config.output_format == "stream-json":
        stream = StreamEmitter()

    skill_registry = {}
    for plugin in plugins:
        skill_registry.update(plugin.skills)

    skill_descriptions = [
        f"{name} — {s.description}" for name, s in skill_registry.items()
    ]

    system_prompt = _build_system_prompt(config, plugins, skill_registry)
    tools = get_all_tools(skill_descriptions)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    log.info(f"Using model: {config.model}")
    for p in plugins:
        log.plugin_loaded(p.name, len(p.skills))
    log.info("Starting task...")

    plugin_names = [p.name for p in plugins]
    if stream:
        stream.system_init(config.model, plugin_names)

    start_time = time.monotonic()
    total_input = 0
    total_output = 0
    total_reasoning = 0

    try:
        return _run_loop(
            config, llm, log, stream, safety, skill_registry,
            messages, tools, start_time,
            total_input, total_output, total_reasoning,
        )
    except Exception as e:
        if stream:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            stream.system_error(str(e))
            stream.result("", is_error=True, duration_ms=duration_ms, iterations=0)
        raise


def _run_loop(
    config, llm, log, stream, safety, skill_registry,
    messages, tools, start_time,
    total_input, total_output, total_reasoning,
):
    for i in range(config.max_iterations):
        log.iteration(i, config.max_iterations)
        response = llm.chat(messages, tools)
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        total_reasoning += response.usage.reasoning_tokens

        # Build assistant message in OpenAI format
        assistant_msg: dict = {"role": "assistant"}
        if response.text:
            assistant_msg["content"] = response.text
        if response.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in response.tool_calls
            ]
        messages.append(assistant_msg)

        # Emit assistant message for stream-json
        if stream:
            content_blocks = _build_content_blocks(response)
            if content_blocks:
                stream.assistant(content_blocks)

        if not response.tool_calls:
            if response.text:
                log.assistant_message(response.text)
            final_text = response.text or ""
            iterations_used = i + 1
            log.usage_summary(total_input, total_output, total_reasoning, iterations_used)
            if stream:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                stream.result(final_text, is_error=False, duration_ms=duration_ms, iterations=iterations_used)
                stream.system_done(iterations_used)
            return final_text

        # Show assistant reasoning before tool calls
        if response.text:
            log.thinking(response.text)

        # Execute each tool call
        for tc in response.tool_calls:
            if tc.name == "use_skill":
                skill_name = tc.arguments.get("skill_name", "")
                if skill_name in skill_registry:
                    skill = skill_registry[skill_name]
                    # Use first sentence, capped for display
                    raw = skill.description or ""
                    desc = raw.split(".")[0].split("—")[0].strip()[:80]
                    log.skill_load(skill_name, desc)
                    result_text = f"Skill loaded. Follow these instructions:\n\n{skill.content}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })
                    if stream:
                        stream.tool_use(tc.id, tc.name, tc.arguments)
                        stream.tool_result(tc.id, tc.name, result_text, error=False)
                else:
                    log.skill_load(skill_name, "NOT FOUND")
                    available = ", ".join(skill_registry.keys())
                    error_text = f"Error: skill '{skill_name}' not found. Available: {available}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": error_text,
                    })
                    if stream:
                        stream.tool_use(tc.id, tc.name, tc.arguments)
                        stream.tool_result(tc.id, tc.name, error_text, error=True)
            else:
                log.tool_call(tc.name, _summarize_args(tc))
                if stream:
                    stream.tool_use(tc.id, tc.name, tc.arguments)
                result = execute_tool(tc.name, tc.arguments, safety, config.project_dir, timeout=config.timeout)
                log.tool_result(result)
                if stream:
                    stream.tool_result(tc.id, tc.name, result, error=False)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

    log.info(f"Reached max iterations ({config.max_iterations})")
    log.usage_summary(total_input, total_output, total_reasoning, config.max_iterations)

    if stream:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        stream.system_error("max iterations reached")
        final_text = messages[-1].get("content", "") if messages else ""
        stream.result(final_text, is_error=True, duration_ms=duration_ms, iterations=config.max_iterations)
        stream.system_done(config.max_iterations)

    return messages[-1].get("content", "") if messages else ""


def _summarize_args(tc) -> str:
    if tc.name == "bash":
        return tc.arguments.get("command", "")
    if tc.name in ("read_file", "write_file"):
        return tc.arguments.get("path", "")
    if tc.name == "list_files":
        return tc.arguments.get("pattern", "")
    if tc.name == "grep":
        return tc.arguments.get("pattern", "")
    return str(tc.arguments)[:100]
