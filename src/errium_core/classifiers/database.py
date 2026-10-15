from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError

_DUPLICATE_MARKERS = (
    "unique constraint",
    "duplicate key",
    "duplicate entry",
    "already exists",
)

# Database libraries recognised by the module path of an exception's MRO, so
# none of them has to be installed (or imported) for Errium to classify them.
_DB_MODULES = (
    "sqlalchemy",
    "django.db",
    "sqlite3",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "pymysql",
    "MySQLdb",
)

# Driver-specific exceptions that are, by type alone, a uniqueness violation.
_UNIQUE_VIOLATION_NAMES = ("UniqueViolation", "UniqueViolationError")


class DatabaseExceptionClassifier:
    @property
    def priority(self) -> int:
        """Below validation, above the generic fallback default."""
        return 140

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify database errors without a hard dependency on any driver.

        Covers SQLAlchemy, Django's ORM (`django.db`), and the sqlite3/psycopg/
        psycopg2/asyncpg/pymysql drivers.
        """
        if not self._is_database_error(exc):
            return None

        if self._is_duplicate(exc):
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
    def _is_database_error(exc: Exception) -> bool:
        """Detect database exceptions by module path, avoiding a direct import."""
        return any(
            klass.__module__ == module or klass.__module__.startswith(module + ".")
            for klass in type(exc).__mro__
            for module in _DB_MODULES
        )

    @classmethod
    def _is_duplicate(cls, exc: Exception) -> bool:
        names = {klass.__name__ for klass in type(exc).__mro__}
        if names.intersection(_UNIQUE_VIOLATION_NAMES):
            return True
        if "IntegrityError" not in names:
            return False
        return cls._looks_like_duplicate(exc)

    @staticmethod
    def _looks_like_duplicate(exc: Exception) -> bool:
        try:
            message = str(exc).lower()
        except Exception:
            return False
        return any(marker in message for marker in _DUPLICATE_MARKERS)
