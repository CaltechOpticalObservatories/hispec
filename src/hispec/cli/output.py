"""Terminal colour, only when stdout is a terminal."""
import os
import sys


def paint(text: str, code: str) -> str:
    """Wrap text in an ANSI colour code, or return it as is when piped."""
    if not code or not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"
