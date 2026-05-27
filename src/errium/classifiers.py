from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


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

        # Map HTTP status codes to standard error categories
        if status_code == 401:
            category = ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            category = ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            category = ErrorCategory.NOT_FOUND
        elif status_code == 409:
            category = ErrorCategory.DUPLICATE
        elif status_code == 422:
            category = ErrorCategory.VALIDATION
        else:
            category = ErrorCategory.INTERNAL

        detail = getattr(exc, "detail", "An unexpected error occurred.")
        message = str(detail) if detail is not None else "An unexpected error occurred."

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

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=422,
            message="Validation failed.",
        )
