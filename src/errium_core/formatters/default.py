import traceback
from typing import Any

from errium_core.config.settings import get_settings
from errium_core.contracts.error import StandardizedError


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

        # Sanitization: in production, hide internal server errors
        if not settings.debug and error.status_code >= 500:
            code = "INTERNAL_SERVER_ERROR"
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
            "details": error.details,
        }

        # Include debug information if enabled and an exception is present
        if settings.debug:
            debug_info: dict[str, Any] = {
                "exception": (
                    error.exception.__class__.__name__ if error.exception else None
                ),
                "message": str(error.exception) if error.exception else None,
                "stack_trace": None,
                "hints": self._get_debug_hints(error),
            }

            if error.exception:
                debug_info["stack_trace"] = "".join(
                    traceback.format_exception(
                        type(error.exception),
                        error.exception,
                        error.exception.__traceback__,
                    )
                )

            formatted_error["debug"] = debug_info

        return formatted_error

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
