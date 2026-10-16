from pydantic import ValidationError

from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError

MALFORMED_BODY_MESSAGE = "Malformed request body."


def is_malformed_body(exc: Exception) -> bool:
    """True when every validation error is "the body is not parseable JSON".

    Works on pydantic's `ValidationError` and on FastAPI's
    `RequestValidationError` (anything with an `errors()` method) without
    importing either.
    """
    errors_fn = getattr(exc, "errors", None)
    if not callable(errors_fn):
        return False
    try:
        errors = list(errors_fn())
    except Exception:
        return False
    return bool(errors) and all(
        isinstance(e, dict) and e.get("type") == "json_invalid" for e in errors
    )


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
