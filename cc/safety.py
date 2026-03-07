"""Safety guardrails: command deny list + path restrictions."""

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    allowed: bool
    reason: str = ""


DENY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\b"), "rm (file deletion)"),
    (re.compile(r"\brmdir\b"), "rmdir (directory deletion)"),
    (re.compile(r"\bunlink\b"), "unlink (file deletion)"),
    (re.compile(r"\bsudo\b"), "sudo (privilege escalation)"),
    (re.compile(r"\bsu\b(?!\w)"), "su (privilege escalation)"),
    (re.compile(r"\bdoas\b"), "doas (privilege escalation)"),
    (re.compile(r"\bshutdown\b"), "shutdown (system control)"),
    (re.compile(r"\breboot\b"), "reboot (system control)"),
    (re.compile(r"\bhalt\b"), "halt (system control)"),
    (re.compile(r"\bmkfs\b"), "mkfs (disk operation)"),
    (re.compile(r"\bfdisk\b"), "fdisk (disk operation)"),
    (re.compile(r"\bdd\b"), "dd (disk operation)"),
    (re.compile(r"\bchmod\b.*-[rR].*\/"), "chmod recursive on root"),
    (re.compile(r"\bchown\b.*-[rR].*\/"), "chown recursive on root"),
    (re.compile(r"\bkill\b"), "kill (process control)"),
    (re.compile(r"\bkillall\b"), "killall (process control)"),
    (re.compile(r"\bpkill\b"), "pkill (process control)"),
    (re.compile(r"git\s+push\s+.*--force"), "git push --force"),
    (re.compile(r"git\s+clean"), "git clean"),
    (re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)"), "pipe to shell"),
    (re.compile(r">\s*/dev/sd"), "write to device"),
]

BLOCKED_PATH_PREFIXES = [
    os.path.expanduser("~/.ssh"),
    os.path.expanduser("~/.aws"),
    "/etc",
    "/private",
]


def _extract_command_portion(command: str) -> str:
    """Strip heredoc bodies and quoted strings to avoid false positives.

    For a command like:
        cat > /tmp/file.txt << 'EOF'
        some text with rm and shutdown
        EOF

    We only want to check: cat > /tmp/file.txt << 'EOF'
    """
    # Remove heredoc bodies: << 'DELIM' ... DELIM or << DELIM ... DELIM
    result = re.sub(
        r"<<-?\s*'?(\w+)'?.*?\n.*?\n\1\b",
        "",
        command,
        flags=re.DOTALL,
    )
    # Remove double-quoted strings (but not the command structure)
    result = re.sub(r'"[^"]*"', '""', result)
    # Remove single-quoted strings
    result = re.sub(r"'[^']*'", "''", result)
    return result


class SafetyChecker:
    def __init__(self, project_dir: str):
        self.project_dir = str(Path(project_dir).resolve())

    def check_command(self, command: str) -> CheckResult:
        # Only check the command portion before heredocs or quoted strings
        # to avoid false positives from words like "shutdown" in comment text
        check_text = _extract_command_portion(command)
        for pattern, description in DENY_PATTERNS:
            if pattern.search(check_text):
                return CheckResult(allowed=False, reason=f"Blocked: {description}")
        return CheckResult(allowed=True)

    def check_path(self, path: str) -> bool:
        resolved = str(Path(path).resolve())
        if not resolved.startswith(self.project_dir):
            return False
        for prefix in BLOCKED_PATH_PREFIXES:
            if resolved.startswith(prefix) and not self.project_dir.startswith(prefix):
                return False
        return True
