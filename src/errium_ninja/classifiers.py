from django.http import Http404
from ninja.errors import HttpError
from ninja.errors import ValidationError as NinjaValidationError

from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class NinjaValidationErrorClassifier:
    @property
    def priority(self) -> int:
        """Higher priority to evaluate before general HTTP error classifiers."""
        return 210

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Django Ninja's ValidationError (wraps pydantic errors)."""
        if not isinstance(exc, NinjaValidationError):
            return None

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=422,
            message="Validation failed.",
        )


class NinjaHttpErrorClassifier:
    @property
    def priority(self) -> int:
        """High priority for HTTP errors."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Django Ninja's HttpError (and its subclasses: AuthenticationError,
        AuthorizationError, Throttled)."""
        if not isinstance(exc, HttpError):
            return None

        category = category_for_status_code(exc.status_code)

        return ClassifiedError(
            category=category,
            status_code=exc.status_code,
            message=exc.message,
        )


class DjangoHttp404Classifier:
    @property
    def priority(self) -> int:
        """High priority for HTTP errors."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Django's Http404, e.g. raised via `get_object_or_404`."""
        if not isinstance(exc, Http404):
            return None

        message = str(exc) or "Resource not found."

        return ClassifiedError(
            category=ErrorCategory.NOT_FOUND,
            status_code=404,
            message=message,
        )
