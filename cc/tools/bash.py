"""Bash tool — run shell commands with safety checks."""

import subprocess
from cc.safety import SafetyChecker

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command. Commands are executed in the project directory. Dangerous commands (rm, sudo, etc.) are blocked.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run"
                }
            },
            "required": ["command"]
        }
    }
}


def execute(arguments: dict, safety: SafetyChecker, project_dir: str) -> str:
    command = arguments.get("command", "")
    check = safety.check_command(command)
    if not check.allowed:
        return f"Blocked: {check.reason}"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=project_dir, timeout=120,
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if not output.strip():
            output = f"(exit code {result.returncode})"
        # Truncate
        lines = output.splitlines()
        if len(lines) > 2000:
            output = "\n".join(lines[:2000]) + f"\n... truncated ({len(lines)} total lines)"
        if len(output.encode()) > 100_000:
            output = output[:100_000] + "\n... truncated (output too large)"
        return output
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 120 seconds"
    except Exception as e:
        return f"Error: {e}"
