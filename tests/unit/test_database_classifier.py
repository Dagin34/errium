from errium_core.classifiers.database import DatabaseExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.categories import ErrorCategory

# Fake SQLAlchemy-style exception types, built without a sqlalchemy dependency.
# The classifier detects SQLAlchemy errors purely by module path, so we fake
# __module__ to exercise that detection.
_SA_MODULE = {"__module__": "sqlalchemy.exc"}
_SQLAlchemyError = type("SQLAlchemyError", (Exception,), _SA_MODULE)
_IntegrityError = type("IntegrityError", (_SQLAlchemyError,), _SA_MODULE)
_OperationalError = type("OperationalError", (_SQLAlchemyError,), _SA_MODULE)


def test_integrity_error_with_unique_violation_is_duplicate():
    exc = _IntegrityError("UNIQUE constraint failed: users.email")
    classifier = DatabaseExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.DUPLICATE
    assert result.status_code == 409


def test_integrity_error_without_duplicate_marker_is_database_error():
    exc = _IntegrityError("NOT NULL constraint failed: users.email")
    classifier = DatabaseExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.DATABASE
    assert result.status_code == 500


def test_other_sqlalchemy_error_is_database_error():
    exc = _OperationalError("could not connect to server")
    classifier = DatabaseExceptionClassifier()
    result = classifier.classify(exc)
    assert result is not None
    assert result.category == ErrorCategory.DATABASE
    assert result.status_code == 500


def test_non_sqlalchemy_exception_is_not_classified():
    exc = ValueError("some unrelated error")
    classifier = DatabaseExceptionClassifier()
    assert classifier.classify(exc) is None


def test_engine_routes_duplicate_key_violation_end_to_end():
    exc = _IntegrityError("duplicate key value violates unique constraint")
    engine = ClassificationEngine()
    result = engine.classify(exc)
    assert result.category == ErrorCategory.DUPLICATE
    assert result.status_code == 409
