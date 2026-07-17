from django.http import Http404
from ninja.errors import AuthenticationError, AuthorizationError, HttpError
from ninja.errors import ValidationError as NinjaValidationError

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.categories import ErrorCategory
from errium_ninja.classifiers import (
    DjangoHttp404Classifier,
    NinjaHttpErrorClassifier,
    NinjaValidationErrorClassifier,
)


def test_ninja_validation_error_classifier():
    exc = NinjaValidationError(
        errors=[{"loc": ["body", "payload", "email"], "msg": "x"}]
    )
    classifier = NinjaValidationErrorClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.VALIDATION
    assert result.status_code == 422


def test_ninja_http_error_classifier():
    exc = HttpError(404, "User not found")
    classifier = NinjaHttpErrorClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404
    assert result.message == "User not found"


def test_ninja_http_error_classifier_covers_subclasses():
    classifier = NinjaHttpErrorClassifier()

    result_auth = classifier.classify(AuthenticationError())
    assert result_auth is not None
    assert result_auth.category == ErrorCategory.AUTHENTICATION
    assert result_auth.status_code == 401

    result_authz = classifier.classify(AuthorizationError())
    assert result_authz is not None
    assert result_authz.category == ErrorCategory.AUTHORIZATION
    assert result_authz.status_code == 403


def test_django_http404_classifier():
    exc = Http404("User not found")
    classifier = DjangoHttp404Classifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404
    assert result.message == "User not found"


def test_classifiers_ignore_unrelated_exceptions():
    assert NinjaValidationErrorClassifier().classify(ValueError("x")) is None
    assert NinjaHttpErrorClassifier().classify(ValueError("x")) is None
    assert DjangoHttp404Classifier().classify(ValueError("x")) is None


def test_engine_falls_back_for_generic_exception_with_ninja_classifiers():
    engine = ClassificationEngine()
    engine.register(NinjaHttpErrorClassifier())
    engine.register(DjangoHttp404Classifier())

    result = engine.classify(RuntimeError("boom"))
    assert result.category == ErrorCategory.INTERNAL
    assert result.status_code == 500
