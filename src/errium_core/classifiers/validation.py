from fastapi.exceptions import RequestValidationError

from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class ValidationExceptionClassifier:
    def classify(self, exc: Exception) -> ClassifiedError | None:
        if not isinstance(exc, RequestValidationError):
            return None

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=422,
            message="Validation failed.",
        )
