"""List files tool — glob pattern search."""

from pathlib import Path
from cc.safety import SafetyChecker

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files matching a glob pattern in the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py', 'src/*.js')"
                }
            },
            "required": ["pattern"]
        }
    }
}


def execute(arguments: dict, safety: SafetyChecker, project_dir: str) -> str:
    pattern = arguments.get("pattern", "*")
    root = Path(project_dir)

    try:
        matches = sorted(root.glob(pattern))
        if not matches:
            return "No files matched."
        rel_paths = [str(m.relative_to(root)) for m in matches[:500]]
        result = "\n".join(rel_paths)
        if len(matches) > 500:
            result += f"\n... and {len(matches) - 500} more"
        return result
    except Exception as e:
        return f"Error: {e}"
