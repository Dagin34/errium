import re
from contextvars import ContextVar
from uuid import uuid4

from errium_core.config.settings import get_settings

TRACE_ID_HEADER = "X-Trace-Id"
REQUEST_ID_HEADER = "X-Request-ID"

# An inbound request id is only reused if it is short and made of safe characters.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:\-]{1,128}$")

_current_trace_id: ContextVar[str | None] = ContextVar("errium_trace_id", default=None)


def generate_trace_id() -> str:
    return str(uuid4())


def current_trace_id() -> str | None:
    """The trace id of the request being handled, if Errium has assigned one.

    Use it from a logging filter or app code to correlate your own log lines
    with the `trace_id` returned to the client.
    """
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str | None) -> None:
    _current_trace_id.set(trace_id)


def resolve_trace_id(request_id: str | None = None) -> str:
    """Pick the trace id for a request.

    A fresh uuid4 by default. If `ERRIUM_TRUST_REQUEST_ID` is enabled and the
    inbound `X-Request-ID` is valid (<=128 safe characters), it is reused.
    """
    if (
        request_id
        and get_settings().trust_request_id
        and _SAFE_REQUEST_ID.match(request_id)
    ):
        return request_id
    return generate_trace_id()
