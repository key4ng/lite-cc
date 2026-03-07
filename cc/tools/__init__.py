"""Built-in tool definitions and execution."""

from cc.tools.bash import TOOL_DEF as BASH_DEF, execute as bash_execute
from cc.tools.read_file import TOOL_DEF as READ_DEF, execute as read_execute
from cc.tools.write_file import TOOL_DEF as WRITE_DEF, execute as write_execute
from cc.tools.list_files import TOOL_DEF as LIST_DEF, execute as list_execute
from cc.tools.grep import TOOL_DEF as GREP_DEF, execute as grep_execute
from cc.safety import SafetyChecker

_SKILL_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": "Load a skill's instructions to follow for the current task. Call this when you need to use a specific skill.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to load"
                }
            },
            "required": ["skill_name"]
        }
    }
}

_TOOLS = {
    "bash": (BASH_DEF, bash_execute),
    "read_file": (READ_DEF, read_execute),
    "write_file": (WRITE_DEF, write_execute),
    "list_files": (LIST_DEF, list_execute),
    "grep": (GREP_DEF, grep_execute),
}


def get_all_tools(skill_descriptions: list[str]) -> list[dict]:
    """Return OpenAI function-calling tool definitions."""
    tools = [defn for defn, _ in _TOOLS.values()]
    skill_tool = _SKILL_TOOL_DEF.copy()
    if skill_descriptions:
        desc = skill_tool["function"]["description"]
        desc += "\n\nAvailable skills:\n" + "\n".join(f"- {s}" for s in skill_descriptions)
        skill_tool["function"]["description"] = desc
    tools.append(skill_tool)
    return tools


def execute_tool(name: str, arguments: dict, safety: SafetyChecker, project_dir: str, timeout: int = 120) -> str:
    """Execute a built-in tool by name. Returns result string."""
    if name not in _TOOLS:
        return f"Error: unknown tool '{name}'"
    _, exec_fn = _TOOLS[name]
    if name == "bash":
        return exec_fn(arguments, safety, project_dir, timeout=timeout)
    return exec_fn(arguments, safety, project_dir)
