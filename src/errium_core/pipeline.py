"""The shared classify -> format path every adapter funnels exceptions through."""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.config.settings import get_settings
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.base import ErrorFormatter
from errium_core.headers import protocol_headers
from errium_core.tracing.trace import (
    TRACE_ID_HEADER,
    generate_trace_id,
    set_current_trace_id,
)

logger = logging.getLogger("errium")

GENERIC_MESSAGE = "An unexpected error occurred."

DetailsSource = Mapping[str, Any] | Callable[[], Mapping[str, Any] | None] | None


@dataclass(slots=True)
class HandledError:
    """A fully rendered error, ready for an adapter to wrap in its response type."""

    status_code: int
    body: dict[str, Any]
    trace_id: str
    headers: dict[str, str] = field(default_factory=dict)


def fallback_error(
    exc: BaseException | None, trace_id: str | None = None
) -> HandledError:
    """The last-resort envelope: generic 500, built without touching `exc` text."""
    trace_id = trace_id or generate_trace_id()
    body: dict[str, Any] = {
        "success": False,
        "status_code": 500,
        "code": ErrorCategory.INTERNAL.value,
        "message": GENERIC_MESSAGE,
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "details": None,
    }
    try:
        if get_settings().debug:
            body["debug"] = {
                "exception": type(exc).__name__ if exc is not None else None,
                "message": None,
                "stack_trace": None,
                "hints": [],
            }
    except Exception:
        pass
    return HandledError(
        status_code=500,
        body=body,
        trace_id=trace_id,
        headers={TRACE_ID_HEADER: trace_id},
    )


def _log(
    exc: BaseException,
    status_code: int,
    category: str,
    trace_id: str,
    method: str | None,
    path: str | None,
) -> None:
    """Log a handled exception on the `errium` logger; never raises.

    >= 500 logs at ERROR with the traceback, anything else at WARNING without one.
    Errium never configures handlers - the application decides where logs go.
    """
    try:
        request = f"{method or '-'} {path or '-'}"
        message = "%s -> %d %s trace_id=%s"
        args = (request, status_code, category, trace_id)
        extra = {
            "errium_trace_id": trace_id,
            "errium_status_code": status_code,
            "errium_category": category,
        }
        if status_code >= 500:
            logger.error(message, *args, exc_info=exc, extra=extra)
        else:
            logger.warning(message, *args, extra=extra)
    except Exception:
        pass


def handle_error(
    exc: Exception,
    *,
    engine: ClassificationEngine,
    formatter: ErrorFormatter,
    details: DetailsSource = None,
    headers: Mapping[str, str] | None = None,
    trace_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> HandledError:
    """Classify `exc` and render the standard envelope. Never raises.

    If anything in the classify/format path fails, a generic 500
    `INTERNAL_SERVER_ERROR` envelope with a fresh trace id is returned instead.
    """
    trace_id = trace_id or generate_trace_id()
    set_current_trace_id(trace_id)
    try:
        classified = engine.classify(exc)
        resolved_details = details() if callable(details) else details
        error = StandardizedError(
            status_code=classified.status_code,
            code=classified.category,
            message=classified.message,
            trace_id=trace_id,
            success=False,
            details=dict(resolved_details) if resolved_details is not None else None,
            exception=exc,
        )
        body = formatter.format(error)
        response_headers = {
            **protocol_headers(exc),
            **(headers or {}),
            TRACE_ID_HEADER: trace_id,
        }
        _log(
            exc,
            classified.status_code,
            str(classified.category),
            trace_id,
            method,
            path,
        )
        return HandledError(
            status_code=classified.status_code,
            body=body,
            trace_id=trace_id,
            headers=response_headers,
        )
    except Exception:
        _log(exc, 500, ErrorCategory.INTERNAL.value, trace_id, method, path)
        return fallback_error(exc, trace_id)
