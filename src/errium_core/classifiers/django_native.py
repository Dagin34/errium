"""Classifier for Django's own exceptions, detected by duck-typing (no import)."""

from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError
from errium_core.safe import safe_str

_TOO_BIG_NAMES = ("RequestDataTooBig", "TooManyFieldsSent", "TooManyFilesSent")


def _has_base(exc: BaseException, module_prefix: str, *names: str) -> bool:
    """True if any class in the MRO is one of `names` living under `module_prefix`."""
    return any(
        klass.__name__ in names and klass.__module__.startswith(module_prefix)
        for klass in type(exc).__mro__
    )


class DjangoExceptionClassifier:
    """Maps Django's framework exceptions to the status Django itself would use.

    Needed because Ninja's and DRF's generic handlers otherwise turn them into
    500s. `validation_status` is the status for `django.core.exceptions.
    ValidationError` - 422 for Ninja (like the other adapters), 400 for DRF.
    """

    def __init__(self, validation_status: int = 422) -> None:
        self.validation_status = validation_status

    @property
    def priority(self) -> int:
        """Below adapter classifiers (200+), above the generic core ones."""
        return 190

    def classify(self, exc: Exception) -> ClassifiedError | None:
        core = "django.core.exceptions"

        if _has_base(exc, "django.http", "Http404"):
            return ClassifiedError(
                category=ErrorCategory.NOT_FOUND,
                status_code=404,
                message=safe_str(exc) or "Resource not found.",
            )
        if _has_base(exc, core, "PermissionDenied"):
            return ClassifiedError(
                category=ErrorCategory.AUTHORIZATION,
                status_code=403,
                message=safe_str(exc)
                or "You do not have permission to perform this action.",
            )
        # Check the "too big" subclasses before their SuspiciousOperation parent.
        if _has_base(exc, core, *_TOO_BIG_NAMES):
            return ClassifiedError(
                category=ErrorCategory.PAYLOAD_TOO_LARGE,
                status_code=413,
                message="The request body is too large.",
            )
        if _has_base(exc, core, "SuspiciousOperation"):
            return ClassifiedError(
                category=ErrorCategory.BAD_REQUEST,
                status_code=400,
                message="The request could not be processed.",
            )
        if _has_base(exc, core, "ValidationError"):
            return ClassifiedError(
                category=ErrorCategory.VALIDATION,
                status_code=self.validation_status,
                message="Validation failed.",
            )
        if _has_base(exc, core, "ObjectDoesNotExist"):
            return ClassifiedError(
                category=ErrorCategory.NOT_FOUND,
                status_code=404,
                message="Resource not found.",
            )
        return None
