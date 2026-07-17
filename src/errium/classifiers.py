from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from errium_core.classifiers.status_mapping import category_for_status_code
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
        category = category_for_status_code(status_code)

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
