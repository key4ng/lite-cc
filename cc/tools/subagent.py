"""spawn_subagent tool — LLM-callable wrapper for run_subagent."""

from cc.safety import SafetyChecker
from cc.output import _short_model_name

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "spawn_subagent",
        "description": (
            "Spawn an isolated subagent with a specific model and task. "
            "The subagent runs independently with its own conversation and returns its final text output. "
            "Use this to delegate subtasks like code review, research, or analysis to a different model."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Task description and context for the subagent",
                },
                "model": {
                    "type": "string",
                    "description": "Model to use, e.g. oci/openai.gpt-5.4. Omit to use the default model.",
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed tool names. Defaults to read-only: read_file, list_files, grep",
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Max iterations. Default 10",
                },
            },
            "required": ["prompt"],
        },
    },
}

_DEFAULT_TOOLS = ["read_file", "list_files", "grep"]


def execute(arguments: dict, safety: SafetyChecker, project_dir: str,
            config=None, plugins=None, timeout: int = 120) -> str:
    """Execute spawn_subagent tool. Returns formatted result string."""
    from cc.subagent import SubagentTask, run_subagent

    prompt = arguments.get("prompt", "")
    model = arguments.get("model", None)
    tools = arguments.get("tools", _DEFAULT_TOOLS)
    max_iterations = arguments.get("max_iterations", 10)

    task = SubagentTask(
        prompt=prompt,
        model=model or (config.model if config else None),
        project_dir=project_dir,
        tools=tools,
        max_iterations=max_iterations,
        timeout=timeout,
    )

    result = run_subagent(task, plugins=plugins, parent_config=config)

    if not result.success:
        return f"Error: subagent failed — {result.error}"

    short_model = _short_model_name(result.model)
    usage_str = f"{result.usage.input_tokens:,} in / {result.usage.output_tokens:,} out"
    return f"[subagent/{short_model}] ({result.iterations_used} iterations, {usage_str})\n\n{result.text or '(no output)'}"
