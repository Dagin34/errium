from django.http import Http404
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.testing import TestClient

from errium_core.config.settings import ErriumSettings, set_settings
from errium_ninja import register_errium


class UserCreateSchema(Schema):
    email: str
    password: str


def create_test_api() -> NinjaAPI:
    api = NinjaAPI()
    register_errium(api)

    @api.post("/users")
    def create_user(request, payload: UserCreateSchema):  # type: ignore[no-untyped-def]
        return payload.dict()

    @api.get("/missing")
    def missing(request):  # type: ignore[no-untyped-def]
        raise Http404("User not found")

    @api.get("/forbidden")
    def forbidden(request):  # type: ignore[no-untyped-def]
        raise HttpError(403, "Forbidden area")

    @api.get("/trigger-500")
    def trigger_error(request):  # type: ignore[no-untyped-def]
        raise RuntimeError("Something went wrong internally")

    return api


def test_ninja_validation_error_beautified():
    client = TestClient(create_test_api())

    response = client.post("/users", json={"email": "x@example.com"})
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["status_code"] == 422
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed."
    assert "trace_id" in data
    assert "timestamp" in data
    # Ninja's synthetic parameter-name wrapper ("payload") must be stripped
    # so the key matches the FastAPI/Flask adapters' flat field name.
    assert data["details"] == {"password": "Password is required."}


def test_ninja_http404_is_standardized():
    client = TestClient(create_test_api())

    response = client.get("/missing")
    assert response.status_code == 404
    data = response.json()

    assert data["success"] is False
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert data["message"] == "User not found"


def test_ninja_http_error_is_standardized():
    client = TestClient(create_test_api())

    response = client.get("/forbidden")
    assert response.status_code == 403
    data = response.json()

    assert data["code"] == "AUTHORIZATION_ERROR"
    assert data["message"] == "Forbidden area"


def test_ninja_internal_error_production():
    set_settings(ErriumSettings(debug=False))
    client = TestClient(create_test_api())

    response = client.get("/trigger-500")
    assert response.status_code == 500
    data = response.json()

    assert data["success"] is False
    assert data["status_code"] == 500
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred."
    assert "debug" not in data


def test_ninja_internal_error_debug():
    set_settings(ErriumSettings(debug=True))
    client = TestClient(create_test_api())

    response = client.get("/trigger-500")
    assert response.status_code == 500
    data = response.json()

    assert "debug" in data
    debug_info = data["debug"]
    assert debug_info["exception"] == "RuntimeError"
    assert debug_info["message"] == "Something went wrong internally"
    assert "RuntimeError: Something went wrong internally" in debug_info["stack_trace"]
