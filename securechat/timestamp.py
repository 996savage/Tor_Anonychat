#timestamp

import os
from datetime import datetime


def _ts() -> str:
    """Return [HH:MM] timestamp string, or empty string if disabled."""
    if os.environ.get("SECURECHAT_TIMESTAMPS", "0") == "1":
        return datetime.now().strftime("[%H:%M] ")
    return ""


def fmt_msg(sender: str, text: str) -> str:
    """
    Format an incoming or outgoing chat message with an optional timestamp.

    Examples (with SECURECHAT_TIMESTAMPS=1):
        fmt_msg("them", "hello")   → "[14:32] them: hello"
        fmt_msg("you",  "hi!")     → "[14:32] you:  hi!"
    """
    return f"{_ts()}{sender}: {text}"


def fmt_system(text: str) -> str:
    """
    Format a system/status message with an optional timestamp.

    Example:
        fmt_system("Guest connected")  → "[14:32] *** Guest connected ***"
    """
    return f"{_ts()}*** {text} ***"
