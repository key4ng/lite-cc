"""Grep tool — search file contents."""

import subprocess
from cc.safety import SafetyChecker

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": "Search file contents for a pattern. Searches recursively in the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (regex)"
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (relative to project dir, default '.')"
                },
                "include": {
                    "type": "string",
                    "description": "File glob to include (e.g. '*.py')"
                }
            },
            "required": ["pattern"]
        }
    }
}


def execute(arguments: dict, safety: SafetyChecker, project_dir: str) -> str:
    pattern = arguments.get("pattern", "")
    search_path = arguments.get("path", ".")
    include = arguments.get("include", "")

    cmd = ["grep", "-rn", "--color=never"]
    if include:
        cmd.extend(["--include", include])
    cmd.extend([pattern, search_path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=project_dir, timeout=30,
        )
        output = result.stdout
        if not output.strip():
            return "No matches found."
        lines = output.splitlines()
        if len(lines) > 200:
            output = "\n".join(lines[:200]) + f"\n... truncated ({len(lines)} total matches)"
        return output
    except subprocess.TimeoutExpired:
        return "Error: search timed out"
    except Exception as e:
        return f"Error: {e}"
