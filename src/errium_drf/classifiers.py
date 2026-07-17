from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError as DRFValidationError

from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class DRFValidationErrorClassifier:
    @property
    def priority(self) -> int:
        """Higher priority to evaluate before the general APIException classifier."""
        return 210

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify DRF's ValidationError (raised by serializers, or manually).

        Unlike the other adapters, this keeps DRF's own status code (400 by
        default) rather than forcing 422 - that's DRF's established REST
        convention and changing it would surprise existing DRF API consumers.
        """
        if not isinstance(exc, DRFValidationError):
            return None

        return ClassifiedError(
            category=ErrorCategory.VALIDATION,
            status_code=exc.status_code,
            message="Validation failed.",
        )


class DRFAPIExceptionClassifier:
    @property
    def priority(self) -> int:
        """High priority for API exceptions."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify DRF's APIException family (NotFound, PermissionDenied,
        AuthenticationFailed, Throttled, etc.)."""
        if not isinstance(exc, APIException):
            return None

        category = category_for_status_code(exc.status_code)

        return ClassifiedError(
            category=category,
            status_code=exc.status_code,
            message=str(exc.detail),
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


class DjangoPermissionDeniedClassifier:
    @property
    def priority(self) -> int:
        """High priority for HTTP errors."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Django's own PermissionDenied (django.core.exceptions),
        distinct from DRF's own PermissionDenied APIException."""
        if not isinstance(exc, DjangoPermissionDenied):
            return None

        message = str(exc) or "You do not have permission to perform this action."

        return ClassifiedError(
            category=ErrorCategory.AUTHORIZATION,
            status_code=403,
            message=message,
        )
