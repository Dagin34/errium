from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class QuotaExceeded(Exception):
    pass


class QuotaClassifier:
    @property
    def priority(self) -> int:
        return 160

    def classify(self, exc: Exception) -> ClassifiedError | None:
        if isinstance(exc, QuotaExceeded):
            return ClassifiedError(
                category=ErrorCategory.CONFLICT,
                status_code=409,
                message="Quota already in use.",
            )
        return None
