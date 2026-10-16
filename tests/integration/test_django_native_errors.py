import pytest
from django.core.exceptions import (
    PermissionDenied,
    RequestDataTooBig,
    SuspiciousOperation,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import IntegrityError, OperationalError
from ninja import NinjaAPI
from ninja.testing import TestClient as NinjaTestClient
from rest_framework.decorators import api_view
from rest_framework.test import APIRequestFactory

from errium_core.config.settings import ErriumSettings, set_settings
from errium_ninja import register_errium

CASES = [
    (PermissionDenied(), 403, "AUTHORIZATION_ERROR"),
    (SuspiciousOperation("x"), 400, "BAD_REQUEST"),
    (RequestDataTooBig("x"), 413, "PAYLOAD_TOO_LARGE"),
    (IntegrityError("UNIQUE constraint failed: t.email"), 409, "DUPLICATE_RESOURCE"),
    (OperationalError("no such table: secret_table"), 500, "INTERNAL_SERVER_ERROR"),
]


@pytest.fixture(autouse=True)
def prod() -> None:
    set_settings(ErriumSettings(debug=False))


@pytest.mark.parametrize(("exc", "status", "code"), CASES)
def test_ninja_django_exceptions(exc: Exception, status: int, code: str) -> None:
    api = NinjaAPI()
    register_errium(api)

    @api.get("/x")
    def view(request):  # type: ignore[no-untyped-def]
        raise exc

    response = NinjaTestClient(api).get("/x")
    assert response.status_code == status
    assert response.json()["code"] == code
    assert "secret_table" not in response.content.decode()


@pytest.mark.parametrize(("exc", "status", "code"), CASES)
def test_drf_django_exceptions(exc: Exception, status: int, code: str) -> None:
    @api_view(["GET"])
    def view(request):  # type: ignore[no-untyped-def]
        raise exc

    response = view(APIRequestFactory().get("/x"))
    assert response.status_code == status
    assert response.data["code"] == code


def test_ninja_django_validation_error_has_details() -> None:
    api = NinjaAPI()
    register_errium(api)

    @api.get("/x")
    def view(request):  # type: ignore[no-untyped-def]
        raise DjangoValidationError({"email": ["Enter a valid email."]})

    response = NinjaTestClient(api).get("/x")
    assert response.status_code == 422
    assert response.json()["details"] == {"email": "Enter a valid email."}


def test_drf_django_validation_error_is_400_with_details() -> None:
    @api_view(["GET"])
    def view(request):  # type: ignore[no-untyped-def]
        raise DjangoValidationError({"email": ["Enter a valid email."]})

    response = view(APIRequestFactory().get("/x"))
    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["details"] == {"email": "Enter a valid email."}


def test_ninja_response_schema_mismatch_is_a_500() -> None:
    api = NinjaAPI()
    register_errium(api)

    @api.get("/bad", response=dict)
    def bad(request):  # type: ignore[no-untyped-def]
        return "not a dict"

    response = NinjaTestClient(api).get("/bad")
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"


def test_ninja_request_validation_still_422() -> None:
    from ninja import Schema

    class Payload(Schema):
        name: str

    api = NinjaAPI()
    register_errium(api)

    @api.post("/x")
    def create(request, payload: Payload):  # type: ignore[no-untyped-def]
        return payload.dict()

    response = NinjaTestClient(api).post("/x", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
