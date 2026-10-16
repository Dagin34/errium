"""Size bounds that keep error responses small and predictable."""

from collections.abc import Mapping
from typing import Any

from errium_core.safe import truncate

MAX_DETAILS_ENTRIES = 50
MAX_DETAIL_KEY_LENGTH = 200
MAX_DETAIL_MESSAGE_LENGTH = 500
MAX_DEBUG_MESSAGE_LENGTH = 2000
MAX_STACK_TRACE_LENGTH = 20000

TRUNCATED_KEY = "_truncated"


def cap_details(details: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Bound a `details` dict: at most 50 entries, short keys and messages.

    When entries are dropped a `"_truncated": "N more"` sentinel is added; it
    is absent whenever nothing was cut.
    """
    if details is None:
        return None

    capped: dict[str, Any] = {}
    for index, (key, value) in enumerate(details.items()):
        if index >= MAX_DETAILS_ENTRIES:
            break
        if isinstance(value, str):
            value = truncate(value, MAX_DETAIL_MESSAGE_LENGTH)
        capped[truncate(str(key), MAX_DETAIL_KEY_LENGTH)] = value

    dropped = len(details) - MAX_DETAILS_ENTRIES
    if dropped > 0:
        capped[TRUNCATED_KEY] = f"{dropped} more"
    return capped


def tail(text: str, limit: int) -> str:
    """Keep the *end* of `text` (the useful part of a stack trace)."""
    if len(text) <= limit:
        return text
    marker = "...[truncated]\n"
    return marker + text[len(text) - (limit - len(marker)) :]
