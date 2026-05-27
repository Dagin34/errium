from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr

from errium import ErriumMiddleware
from errium.handlers.validation_handler import validation_exception_handler
from errium_core.config.settings import ErriumSettings, set_settings


class UserCreateSchema(BaseModel):
    email: EmailStr
    password: str


# Helper to build our test app
def create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErriumMiddleware)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.post("/users")
    def create_user(user: UserCreateSchema):
        return {"email": user.email}

    @app.get("/trigger-500")
    def trigger_error():
        raise RuntimeError("Something went wrong internally")

    return app


def test_fastapi_validation_error_beautified():
    app = create_test_app()
    client = TestClient(app)

    # 1. Test invalid payload (email is not a valid email, password missing)
    payload = {"email": "not-an-email"}
    response = client.post("/users", json=payload)

    assert response.status_code == 422
    data = response.json()

    # Verify standard Errium format
    assert data["success"] is False
    assert data["status_code"] == 422
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed."
    assert "trace_id" in data
    assert "timestamp" in data

    # Verify details are beautified and normalized
    details = data["details"]
    assert "email" in details
    assert details["email"] == "Invalid email format."
    assert "password" in details
    assert details["password"] == "Password is required."


def test_fastapi_internal_error_production():
    # Force production mode
    set_settings(ErriumSettings(debug=False))

    app = create_test_app()
    client = TestClient(app)

    response = client.get("/trigger-500")
    assert response.status_code == 500

    data = response.json()
    assert data["success"] is False
    assert data["status_code"] == 500
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred."
    assert "debug" not in data


def test_fastapi_internal_error_debug():
    # Force debug mode
    set_settings(ErriumSettings(debug=True))

    app = create_test_app()
    client = TestClient(app)

    response = client.get("/trigger-500")
    assert response.status_code == 500

    data = response.json()
    assert data["success"] is False
    assert data["status_code"] == 500
    # In debug mode, code and message are NOT sanitized
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred."

    # In debug mode, traceback and metadata are visible
    assert "debug" in data
    debug_info = data["debug"]
    assert debug_info["exception"] == "RuntimeError"
    assert debug_info["message"] == "Something went wrong internally"
    assert "RuntimeError: Something went wrong internally" in debug_info["stack_trace"]
