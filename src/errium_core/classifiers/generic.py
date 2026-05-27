from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class GenericExceptionClassifier:
    def classify(self, exc: Exception) -> ClassifiedError:
        return ClassifiedError(
            category=ErrorCategory.INTERNAL,
            status_code=500,
            message="An unexpected error occurred.",
        )
