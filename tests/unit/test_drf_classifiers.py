from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.categories import ErrorCategory
from errium_drf.classifiers import (
    DjangoHttp404Classifier,
    DjangoPermissionDeniedClassifier,
    DRFAPIExceptionClassifier,
    DRFValidationErrorClassifier,
)


def test_drf_validation_error_classifier_keeps_drf_status_code():
    exc = DRFValidationError({"email": ["Enter a valid email address."]})
    classifier = DRFValidationErrorClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.VALIDATION
    assert result.status_code == 400
    assert result.message == "Validation failed."


def test_drf_api_exception_classifier():
    exc = NotFound("User not found")
    classifier = DRFAPIExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404
    assert result.message == "User not found"


def test_drf_api_exception_classifier_auth_statuses():
    classifier = DRFAPIExceptionClassifier()
    result = classifier.classify(AuthenticationFailed())
    assert result is not None
    assert result.category == ErrorCategory.AUTHENTICATION
    assert result.status_code == 401


def test_django_http404_classifier():
    exc = Http404("User not found")
    classifier = DjangoHttp404Classifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404


def test_django_permission_denied_classifier():
    exc = DjangoPermissionDenied("Nope")
    classifier = DjangoPermissionDeniedClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.AUTHORIZATION
    assert result.status_code == 403
    assert result.message == "Nope"


def test_classifiers_ignore_unrelated_exceptions():
    assert DRFValidationErrorClassifier().classify(ValueError("x")) is None
    assert DRFAPIExceptionClassifier().classify(ValueError("x")) is None
    assert DjangoHttp404Classifier().classify(ValueError("x")) is None
    assert DjangoPermissionDeniedClassifier().classify(ValueError("x")) is None


def test_engine_falls_back_for_generic_exception_with_drf_classifiers():
    engine = ClassificationEngine()
    engine.register(DRFAPIExceptionClassifier())
    engine.register(DjangoHttp404Classifier())
    engine.register(DjangoPermissionDeniedClassifier())

    result = engine.classify(RuntimeError("boom"))
    assert result.category == ErrorCategory.INTERNAL
    assert result.status_code == 500
