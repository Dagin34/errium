"""Helpers that turn arbitrary exceptions into text without ever raising."""

_TRUNCATION_MARKER = "...[truncated]"

DEFAULT_TEXT_LIMIT = 2000


def truncate(text: str, limit: int) -> str:
    """Cut `text` to at most `limit` characters, marking the cut."""
    if len(text) <= limit:
        return text
    if limit <= len(_TRUNCATION_MARKER):
        return text[:limit]
    return text[: limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def safe_str(exc: BaseException, limit: int = DEFAULT_TEXT_LIMIT) -> str:
    """Render an exception as text; guaranteed not to raise.

    Tries `str(exc)`, then `repr(exc)`, then the bare class name, so an
    exception whose `__str__`/`__repr__` is broken (or whose args hold
    unprintable objects) can never break Errium's own error path. The result is
    truncated to `limit` characters.
    """
    for render in (str, repr):
        try:
            text = render(exc)
        except Exception:
            continue
        if isinstance(text, str):
            return truncate(text, limit)

    try:
        return truncate(type(exc).__name__, limit)
    except Exception:
        return "Exception"
