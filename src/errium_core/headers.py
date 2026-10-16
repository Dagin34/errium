"""Protocol headers worth carrying from an exception onto the error response."""

from collections.abc import Iterable
from typing import Any

_ALLOWED_HEADERS = {
    "allow": "Allow",
    "retry-after": "Retry-After",
    "www-authenticate": "WWW-Authenticate",
    "location": "Location",
    "content-range": "Content-Range",
}


def _pairs(headers: Any) -> Iterable[tuple[Any, Any]]:
    if headers is None:
        return []
    items = getattr(headers, "items", None)
    if callable(items):
        return list(items())
    try:
        return [(name, value) for name, value in headers]
    except (TypeError, ValueError):
        return []


def protocol_headers(exc: BaseException) -> dict[str, str]:
    """Collect allow-listed headers an exception already knows about.

    Looks at `exc.get_headers()` (Werkzeug), `exc.headers` and
    `exc.response.headers`, and keeps only `Allow`, `Retry-After`,
    `WWW-Authenticate`, `Location` and `Content-Range`. Never raises.
    """
    collected: list[tuple[Any, Any]] = []
    try:
        for source in (exc, getattr(exc, "response", None)):
            if source is None:
                continue
            get_headers = getattr(source, "get_headers", None)
            if callable(get_headers):
                try:
                    collected.extend(_pairs(get_headers()))
                except Exception:
                    pass
            collected.extend(_pairs(getattr(source, "headers", None)))
    except Exception:
        return {}

    result: dict[str, str] = {}
    for name, value in collected:
        canonical = _ALLOWED_HEADERS.get(str(name).lower())
        text = str(value)
        if canonical and "\r" not in text and "\n" not in text:
            result.setdefault(canonical, text)
    return result
