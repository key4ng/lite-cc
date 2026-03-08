"""Colored terminal output for cc agent loop."""

import re
import sys
from datetime import datetime


# ANSI color codes
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[37m"

TAG_STYLES = {
    "cc":        (CYAN, BOLD),
    "tool":      (YELLOW, BOLD),
    "result":    ("\033[90m", ""),
    "plugin":    (GREEN, BOLD),
    "skill":     (MAGENTA, BOLD),
    "thinking":  (BLUE, DIM),
    "error":     ("\033[31m", BOLD),
}


def _short_model_name(model: str) -> str:
    """Extract a short display name from a model string.

    'oci/openai.gpt-5.2' -> 'gpt-5.2'
    'anthropic/claude-3-sonnet-20240229' -> 'claude-3-sonnet'
    'openai/gpt-4o' -> 'gpt-4o'
    """
    name = model.split("/")[-1]
    # Strip provider prefixes like 'openai.'
    if "." in name and name.split(".")[0] in ("openai", "anthropic", "meta"):
        name = name.split(".", 1)[1]
    # Strip date suffixes like -20240229
    name = re.sub(r"-\d{8}$", "", name)
    return name


class Logger:
    def __init__(self, verbose: bool = False, model: str = ""):
        self.verbose = verbose
        self._tool_count = 0
        self._model_tag = _short_model_name(model) if model else "model"

    def log(self, tag: str, message: str, verbose_only: bool = False):
        if verbose_only and not self.verbose:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        color, style = TAG_STYLES.get(tag, (WHITE, ""))
        prefix = f"{DIM}{ts}{RESET} {style}{color}[{tag}]{RESET}"
        print(f"{prefix} {message}", file=sys.stderr, flush=True)

    def tool_call(self, name: str, summary: str):
        self._tool_count += 1
        if self.verbose:
            self.log("tool", f"{name}: {summary}")
        else:
            clean = _clean_command(name, summary)
            self.log("tool", f"{name}: {_compact(clean, 90)}")

    def tool_result(self, result: str):
        self.log("result", _truncate(result, 200), verbose_only=True)

    def plugin_loaded(self, name: str, skill_count: int):
        self.log("plugin", f"{name} ({skill_count} skills)")

    def skill_load(self, name: str, description: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        color, style = TAG_STYLES["skill"]
        prefix = f"{DIM}{ts}{RESET} {style}{color}[skill: {name}]{RESET}"
        msg = description or "loaded"
        print(f"{prefix} {msg}", file=sys.stderr, flush=True)

    def thinking(self, text: str):
        """Log model reasoning between tool calls — tagged with model name."""
        ts = datetime.now().strftime("%H:%M:%S")
        tag = self._model_tag
        color, style = TAG_STYLES["thinking"]
        prefix = f"{DIM}{ts}{RESET} {style}{color}[{tag}]{RESET}"
        if self.verbose:
            print(f"{prefix} {text}", file=sys.stderr, flush=True)
        else:
            clean = text.strip().replace("\n", " ")
            if len(clean) > 120:
                clean = clean[:120] + "..."
            print(f"{prefix} {clean}", file=sys.stderr, flush=True)

    def assistant_message(self, text: str):
        """Log the final response — tagged as [cc]."""
        self.log("cc", text)

    def info(self, message: str):
        self.log("cc", message)

    def debug(self, message: str):
        self.log("cc", message, verbose_only=True)

    def iteration(self, i: int, max_iter: int):
        self.log("cc", f"Iteration {i + 1}/{max_iter}", verbose_only=True)


def _clean_command(tool_name: str, summary: str) -> str:
    """Make tool summaries human-readable in normal mode.

    Strips boilerplate like 'source ~/.config/squire/env.sh &&',
    collapses inline python scripts to a description, etc.
    """
    if tool_name != "bash":
        return summary

    cmd = summary.strip()

    # Strip common prefixes
    cmd = re.sub(r"^source\s+\S+\s*&&\s*", "", cmd)
    cmd = re.sub(r"^cd\s+\S+\s*&&\s*", "", cmd)

    # Collapse inline python to just what it's doing
    if re.match(r"python3?\s+-\s*<<", cmd):
        # Try to extract a meaningful description from the script
        # Look for key operations: json.load, open(), subprocess, kubectl, etc.
        match = re.search(r"open\(['\"]([^'\"]+)['\"]\)", summary)
        if match:
            return f"python3 (processing {match.group(1)})"
        return "python3 (inline script)"

    # Collapse python -c to short form
    if re.match(r"python3?\s+-c\s+", cmd):
        return "python3 (inline expression)"

    # Strip heredoc body for display
    cmd = re.sub(r"\s*<<-?\s*'?\w+'?\n.*", " << ...", cmd, flags=re.DOTALL)

    return cmd


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text.replace("\n", " ")
    return text[:max_len].replace("\n", " ") + "..."


def _compact(text: str, max_len: int) -> str:
    line = text.split("\n")[0].strip()
    if len(line) <= max_len:
        return line
    return line[:max_len] + "..."
