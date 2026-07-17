from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError

_DUPLICATE_MARKERS = (
    "unique constraint",
    "duplicate key",
    "duplicate entry",
    "already exists",
)


class DatabaseExceptionClassifier:
    @property
    def priority(self) -> int:
        """Below validation, above the generic fallback default."""
        return 140

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify SQLAlchemy errors without a hard dependency on sqlalchemy."""
        if not self._is_sqlalchemy_error(exc):
            return None

        is_integrity_error = exc.__class__.__name__ == "IntegrityError"
        if is_integrity_error and self._looks_like_duplicate(exc):
            return ClassifiedError(
                category=ErrorCategory.DUPLICATE,
                status_code=409,
                message="A resource with these details already exists.",
            )

        return ClassifiedError(
            category=ErrorCategory.DATABASE,
            status_code=500,
            message="A database error occurred.",
        )

    @staticmethod
    def _is_sqlalchemy_error(exc: Exception) -> bool:
        """Detect SQLAlchemy exceptions by module path, avoiding a direct import."""
        return any(
            klass.__module__.startswith("sqlalchemy.") for klass in type(exc).__mro__
        )

    @staticmethod
    def _looks_like_duplicate(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(marker in message for marker in _DUPLICATE_MARKERS)
