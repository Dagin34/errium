from werkzeug.exceptions import Forbidden, NotFound, Unauthorized

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.categories import ErrorCategory
from errium_flask.classifiers import WerkzeugHTTPExceptionClassifier


def test_werkzeug_http_exception_classifier_not_found():
    exc = NotFound(description="User not found")
    classifier = WerkzeugHTTPExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404
    assert result.message == "User not found"


def test_werkzeug_http_exception_classifier_auth_statuses():
    classifier = WerkzeugHTTPExceptionClassifier()

    result_auth = classifier.classify(Unauthorized(description="Unauthorized token"))
    assert result_auth is not None
    assert result_auth.category == ErrorCategory.AUTHENTICATION

    result_forbidden = classifier.classify(Forbidden(description="Forbidden area"))
    assert result_forbidden is not None
    assert result_forbidden.category == ErrorCategory.AUTHORIZATION


def test_werkzeug_classifier_ignores_non_http_exceptions():
    classifier = WerkzeugHTTPExceptionClassifier()
    assert classifier.classify(ValueError("not an http exception")) is None


def test_engine_falls_back_for_generic_exception_with_werkzeug_classifier():
    engine = ClassificationEngine()
    engine.register(WerkzeugHTTPExceptionClassifier())

    result = engine.classify(RuntimeError("boom"))
    assert result.category == ErrorCategory.INTERNAL
    assert result.status_code == 500
