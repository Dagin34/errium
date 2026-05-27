from pydantic import ValidationError

from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class ValidationExceptionClassifier:
    @property
    def priority(self) -> int:
        return 150

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify validation errors without direct framework imports."""
        is_pydantic_val = isinstance(exc, ValidationError)
        is_fastapi_val = exc.__class__.__name__ == "RequestValidationError"

        if not (is_pydantic_val or is_fastapi_val):
            return None

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=422,
            message="Validation failed.",
        )
