import traceback
from typing import Any

from errium_core.classifiers.status_mapping import (
    SAFE_5XX_MESSAGES,
    category_for_status_code,
)
from errium_core.config.settings import get_settings
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.error import StandardizedError
from errium_core.limits import (
    MAX_DEBUG_MESSAGE_LENGTH,
    MAX_STACK_TRACE_LENGTH,
    cap_details,
    tail,
)
from errium_core.safe import safe_str, truncate


class DefaultFormatter:
    def format(
        self,
        error: StandardizedError,
    ) -> dict[str, Any]:
        """Format the standardized error into a dictionary according to settings."""
        settings = get_settings()

        # By default, use values from the standardized error
        code = error.code
        message = error.message

        details = error.details

        # Sanitization: in production, no exception text or details of a server
        # error ever reaches the client. 502/503/504 keep a meaningful category
        # with a generic message; every other 5xx collapses to a 500-style code.
        if not settings.debug and error.status_code >= 500:
            details = None
            category = category_for_status_code(error.status_code)
            if category in SAFE_5XX_MESSAGES:
                code = category.value
                message = SAFE_5XX_MESSAGES[category]
            else:
                code = ErrorCategory.INTERNAL.value
                message = "An unexpected error occurred."

        formatted_error: dict[str, Any] = {
            "success": error.success,
            "status_code": error.status_code,
            "code": code,
            "message": message,
            "trace_id": error.trace_id,
            "timestamp": (
                error.timestamp.isoformat()
                if hasattr(error.timestamp, "isoformat")
                else str(error.timestamp)
            ),
            "details": cap_details(details),
        }

        # Include debug information if enabled and an exception is present
        if settings.debug:
            debug_info: dict[str, Any] = {
                "exception": (
                    error.exception.__class__.__name__ if error.exception else None
                ),
                "message": (
                    self._debug_message(error.exception) if error.exception else None
                ),
                "stack_trace": None,
                "hints": self._get_debug_hints(error),
            }

            if error.exception:
                debug_info["stack_trace"] = self._format_stack_trace(error.exception)

            formatted_error["debug"] = debug_info

        return formatted_error

    @staticmethod
    def _redacted_validation_message(exc: Exception) -> str | None:
        """Describe a validation error's `errors()` without echoing request input.

        pydantic/FastAPI errors carry the offending `input` (and `ctx`), which in
        a debug response would hand a submitted password straight back. Only
        `loc`, `msg` and `type` are kept. Returns None for non-validation errors.
        """
        errors_fn = getattr(exc, "errors", None)
        if not callable(errors_fn):
            return None
        try:
            errors = list(errors_fn())
            if not errors or not all(
                isinstance(e, dict) and "loc" in e and "msg" in e for e in errors
            ):
                return None
            return "; ".join(
                f"{'.'.join(str(part) for part in e['loc']) or 'field'}: "
                f"{e['msg']} [{e.get('type', 'error')}]"
                for e in errors
            )
        except Exception:
            return None

    @classmethod
    def _debug_message(cls, exc: Exception) -> str:
        redacted = cls._redacted_validation_message(exc)
        if redacted is not None:
            return truncate(redacted, MAX_DEBUG_MESSAGE_LENGTH)
        return safe_str(exc, MAX_DEBUG_MESSAGE_LENGTH)

    @classmethod
    def _format_stack_trace(cls, exc: Exception) -> str:
        try:
            redacted = cls._redacted_validation_message(exc)
            if redacted is not None:
                # Rebuild the trace so the final line carries the redacted text.
                lines = traceback.format_tb(exc.__traceback__)
                lines.append(
                    f"{type(exc).__module__}.{type(exc).__qualname__}: {redacted}"
                )
                text = "".join(lines)
            else:
                text = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
        except Exception:
            text = f"{type(exc).__name__}: {safe_str(exc)}"
        return tail(text, MAX_STACK_TRACE_LENGTH)

    def _get_debug_hints(self, error: StandardizedError) -> list[str]:
        """Generate helpful development suggestions based on status code and code."""
        hints = []
        if error.status_code == 422:
            hints.append("Check the 'details' field for specific validation failures.")
        elif error.status_code == 404:
            hints.append("Verify the resource ID or path exists in the database.")
        elif error.status_code == 401 or error.status_code == 403:
            hints.append("Check request authentication headers and scopes.")
        elif error.status_code >= 500:
            hints.append(
                "An internal database or backend logic error occurred. "
                "Check backend logs."
            )
        return hints
