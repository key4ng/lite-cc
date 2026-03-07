"""Read file tool."""

from pathlib import Path
from cc.safety import SafetyChecker

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file. Path must be inside the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (absolute or relative to project dir)"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start from (1-based, optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max lines to read (optional)"
                }
            },
            "required": ["path"]
        }
    }
}


def execute(arguments: dict, safety: SafetyChecker, project_dir: str) -> str:
    raw_path = arguments.get("path", "")
    path = Path(raw_path) if Path(raw_path).is_absolute() else Path(project_dir) / raw_path

    if not safety.check_path(str(path)):
        return f"Denied: path '{raw_path}' is outside the project directory"

    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return f"Error: file not found: {raw_path}"
    except Exception as e:
        return f"Error: {e}"

    offset = arguments.get("offset", 1) - 1
    limit = arguments.get("limit", len(lines))
    selected = lines[max(0, offset):offset + limit]

    numbered = [f"{i + offset + 1:>6}\t{line}" for i, line in enumerate(selected)]
    return "\n".join(numbered)
