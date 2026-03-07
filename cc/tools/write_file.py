"""Write file tool."""

from pathlib import Path
from cc.safety import SafetyChecker

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file. Path must be inside the project directory. Creates parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to write to (absolute or relative to project dir)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }
    }
}


def execute(arguments: dict, safety: SafetyChecker, project_dir: str) -> str:
    raw_path = arguments.get("path", "")
    content = arguments.get("content", "")
    path = Path(raw_path) if Path(raw_path).is_absolute() else Path(project_dir) / raw_path

    if not safety.check_path(str(path)):
        return f"Denied: path '{raw_path}' is outside the project directory"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"Wrote {len(content)} bytes to {raw_path}"
    except Exception as e:
        return f"Error: {e}"
