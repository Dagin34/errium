from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from errium.classifiers import (
    FastAPIHTTPExceptionClassifier,
    FastAPIValidationErrorClassifier,
)
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.classifiers.validation import ValidationExceptionClassifier
from errium_core.contracts.categories import ErrorCategory


def test_validation_exception_classifier_pydantic():
    # Construct a raw Pydantic ValidationError
    # We can create one by compiling a dummy schema or mocking it, or raise one
    # Let's construct a genuine ValidationError using Pydantic custom errors
    try:
        raise ValidationError.from_exception_data(
            "dummy_model",
            [
                InitErrorDetails(
                    type=PydanticCustomError("missing", "Field required"),
                    loc=("password",),
                    input=None,
                )
            ],
        )
    except ValidationError as exc:
        classifier = ValidationExceptionClassifier()
        result = classifier.classify(exc)
        assert result is not None
        assert result.category == ErrorCategory.VALIDATION
        assert result.status_code == 422
        assert result.message == "Validation failed."


def test_validation_exception_classifier_fastapi():
    # Construct a RequestValidationError
    exc = RequestValidationError(errors=[{"loc": ["body", "email"], "msg": "invalid"}])
    classifier = ValidationExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.VALIDATION
    assert result.status_code == 422


def test_fastapi_validation_error_classifier():
    exc = RequestValidationError(errors=[])
    classifier = FastAPIValidationErrorClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.VALIDATION
    assert result.status_code == 422


def test_fastapi_http_exception_classifier():
    from fastapi import HTTPException

    exc = HTTPException(status_code=404, detail="User not found")
    classifier = FastAPIHTTPExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.NOT_FOUND
    assert result.status_code == 404
    assert result.message == "User not found"

    # Test other statuses
    exc_auth = HTTPException(status_code=401, detail="Unauthorized token")
    result_auth = classifier.classify(exc_auth)
    assert result_auth.category == ErrorCategory.AUTHENTICATION

    exc_forb = HTTPException(status_code=403, detail="Forbidden area")
    result_forb = classifier.classify(exc_forb)
    assert result_forb.category == ErrorCategory.AUTHORIZATION


def test_generic_exception_fallback():
    exc = ValueError("Some generic database issue")
    engine = ClassificationEngine()
    result = engine.classify(exc)
    # The default registered fallback should categorize it as INTERNAL
    assert result.category == ErrorCategory.INTERNAL
    assert result.status_code == 500
    assert result.message == "An unexpected error occurred."
