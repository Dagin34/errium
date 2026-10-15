import sqlite3

import pytest
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    RequestDataTooBig,
    SuspiciousOperation,
    TooManyFieldsSent,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import DatabaseError, IntegrityError, OperationalError
from django.http import Http404

from errium_core.classifiers.database import DatabaseExceptionClassifier
from errium_core.classifiers.django_native import DjangoExceptionClassifier
from errium_core.normalizers.django_validation import flatten_django_validation_error


@pytest.mark.parametrize(
    ("exc", "status", "category"),
    [
        (PermissionDenied(), 403, "AUTHORIZATION_ERROR"),
        (SuspiciousOperation("x"), 400, "BAD_REQUEST"),
        (RequestDataTooBig("x"), 413, "PAYLOAD_TOO_LARGE"),
        (TooManyFieldsSent("x"), 413, "PAYLOAD_TOO_LARGE"),
        (
            ObjectDoesNotExist("User matching query does not exist."),
            404,
            "RESOURCE_NOT_FOUND",
        ),
        (Http404("nope"), 404, "RESOURCE_NOT_FOUND"),
        (DjangoValidationError("bad"), 422, "VALIDATION_ERROR"),
    ],
)
def test_django_exceptions(exc: Exception, status: int, category: str) -> None:
    result = DjangoExceptionClassifier().classify(exc)
    assert result is not None
    assert (result.status_code, result.category) == (status, category)


def test_validation_status_is_configurable() -> None:
    result = DjangoExceptionClassifier(validation_status=400).classify(
        DjangoValidationError("bad")
    )
    assert result is not None and result.status_code == 400


def test_model_does_not_exist_subclass_is_404() -> None:
    class Missing(ObjectDoesNotExist):
        pass

    result = DjangoExceptionClassifier().classify(Missing("leaky internal text"))
    assert result is not None
    assert result.status_code == 404
    assert "leaky" not in result.message


def test_unrelated_exception_is_ignored() -> None:
    assert DjangoExceptionClassifier().classify(ValueError("x")) is None


def test_flatten_validation_error_dict_and_list() -> None:
    err = DjangoValidationError(
        {"email": ["Enter a valid email.", "Too short."], "__all__": ["Nope."]}
    )
    assert flatten_django_validation_error(err) == {
        "email": "Enter a valid email.; Too short.",
        "_": "Nope.",
    }
    assert flatten_django_validation_error(DjangoValidationError(["a", "b"])) == {
        "_": "a; b"
    }


@pytest.mark.parametrize(
    ("exc", "status", "category"),
    [
        (
            IntegrityError("UNIQUE constraint failed: app_user.email"),
            409,
            "DUPLICATE_RESOURCE",
        ),
        (
            IntegrityError("duplicate key value violates unique constraint"),
            409,
            "DUPLICATE_RESOURCE",
        ),
        (
            IntegrityError("NOT NULL constraint failed: app_user.email"),
            500,
            "DATABASE_ERROR",
        ),
        (OperationalError("no such table"), 500, "DATABASE_ERROR"),
        (DatabaseError("boom"), 500, "DATABASE_ERROR"),
        (
            sqlite3.IntegrityError("UNIQUE constraint failed: t.c"),
            409,
            "DUPLICATE_RESOURCE",
        ),
        (sqlite3.OperationalError("database is locked"), 500, "DATABASE_ERROR"),
    ],
)
def test_database_classifier_covers_django_and_drivers(
    exc: Exception, status: int, category: str
) -> None:
    result = DatabaseExceptionClassifier().classify(exc)
    assert result is not None
    assert (result.status_code, result.category) == (status, category)


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("psycopg2.errors", "UniqueViolation"),
        ("asyncpg.exceptions", "UniqueViolationError"),
        ("pymysql.err", "IntegrityError"),
        ("psycopg.errors", "IntegrityError"),
    ],
)
def test_driver_exceptions_matched_by_module_path(module: str, name: str) -> None:
    exc_type = type(name, (Exception,), {"__module__": module})
    result = DatabaseExceptionClassifier().classify(
        exc_type("Duplicate entry 'a' for key 'x'")
    )
    assert result is not None
    assert result.category == "DUPLICATE_RESOURCE"


def test_unrelated_module_is_not_a_database_error() -> None:
    exc_type = type("IntegrityError", (Exception,), {"__module__": "myapp.errors"})
    assert DatabaseExceptionClassifier().classify(exc_type("x")) is None
