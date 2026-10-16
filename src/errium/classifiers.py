from http import HTTPStatus

from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.classifiers.validation import (
    MALFORMED_BODY_MESSAGE,
    is_malformed_body,
)
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


def _phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "An unexpected error occurred."


class FastAPIHTTPExceptionClassifier:
    @property
    def priority(self) -> int:
        """High priority for HTTP exceptions."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Starlette and FastAPI HTTPExceptions."""
        if not isinstance(exc, FastAPIHTTPException | StarletteHTTPException):
            return None

        status_code = exc.status_code
        category = category_for_status_code(status_code)

        # A string detail is the message. A structured (dict/list) detail is
        # exposed through `details` instead, and the message is the HTTP phrase.
        detail = getattr(exc, "detail", None)
        message = detail if isinstance(detail, str) else _phrase(status_code)

        return ClassifiedError(
            category=category,
            status_code=status_code,
            message=message,
        )


class FastAPIValidationErrorClassifier:
    @property
    def priority(self) -> int:
        """Higher priority to evaluate before general HTTP exception classifiers."""
        return 210

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify FastAPI RequestValidationError."""
        if not isinstance(exc, RequestValidationError):
            return None

        if is_malformed_body(exc):
            return ClassifiedError(
                category=ErrorCategory.BAD_REQUEST,
                status_code=400,
                message=MALFORMED_BODY_MESSAGE,
            )

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=422,
            message="Validation failed.",
        )
