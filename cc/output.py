"""Colored terminal output for cc agent loop."""

import sys


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
    "result":    (DIM, ""),
    "skill":     (MAGENTA, BOLD),
    "assistant": (GREEN, BOLD),
    "error":     ("\033[31m", BOLD),
}


class Logger:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, tag: str, message: str, verbose_only: bool = False):
        """Print a tagged log line to stderr.

        Args:
            tag: The log tag (cc, tool, result, skill, assistant, error)
            message: The message to display
            verbose_only: If True, only show in verbose mode
        """
        if verbose_only and not self.verbose:
            return

        color, style = TAG_STYLES.get(tag, (WHITE, ""))
        prefix = f"{style}{color}[{tag}]{RESET}"
        print(f"{prefix} {message}", file=sys.stderr, flush=True)

    def tool_call(self, name: str, summary: str):
        """Log a tool call — always visible, but compact in normal mode."""
        if self.verbose:
            self.log("tool", f"{name}: {summary}")
        else:
            self.log("tool", f"{name}: {_compact(summary, 80)}")

    def tool_result(self, result: str):
        """Log a tool result — only in verbose mode."""
        self.log("result", _truncate(result, 200), verbose_only=True)

    def skill_load(self, name: str):
        """Log a skill being loaded — always visible."""
        self.log("skill", f"Loading: {name}")

    def assistant_message(self, text: str):
        """Log the final assistant response — always visible."""
        self.log("assistant", text)

    def info(self, message: str):
        """Log an info message — always visible."""
        self.log("cc", message)

    def debug(self, message: str):
        """Log a debug message — verbose only."""
        self.log("cc", message, verbose_only=True)

    def iteration(self, i: int, max_iter: int):
        """Log iteration progress — verbose only."""
        self.log("cc", f"Iteration {i + 1}/{max_iter}", verbose_only=True)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text.replace("\n", " ")
    return text[:max_len].replace("\n", " ") + "..."


def _compact(text: str, max_len: int) -> str:
    """Single line, trimmed."""
    line = text.split("\n")[0].strip()
    if len(line) <= max_len:
        return line
    return line[:max_len] + "..."
