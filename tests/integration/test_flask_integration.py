from flask import Flask, abort, request
from pydantic import BaseModel

from errium_core.config.settings import ErriumSettings, set_settings
from errium_flask import ErriumFlask


class UserCreateSchema(BaseModel):
    email: str
    password: str


def create_test_app() -> Flask:
    app = Flask(__name__)
    app.testing = True
    ErriumFlask(app)

    @app.post("/users")
    def create_user():
        payload = UserCreateSchema.model_validate(request.get_json())
        return {"email": payload.email}

    @app.get("/missing")
    def missing():
        abort(404, description="User not found")

    @app.get("/trigger-500")
    def trigger_error():
        raise RuntimeError("Something went wrong internally")

    return app


def test_flask_validation_error_beautified():
    app = create_test_app()
    client = app.test_client()

    response = client.post("/users", json={"password": "hunter2"})
    assert response.status_code == 422
    data = response.get_json()

    assert data["success"] is False
    assert data["status_code"] == 422
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed."
    assert "trace_id" in data
    assert "timestamp" in data
    assert data["details"]["email"] == "Email is required."


def test_flask_http_exception_is_standardized():
    app = create_test_app()
    client = app.test_client()

    response = client.get("/missing")
    assert response.status_code == 404
    data = response.get_json()

    assert data["success"] is False
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert data["message"] == "User not found"


def test_flask_internal_error_production():
    set_settings(ErriumSettings(debug=False))

    app = create_test_app()
    client = app.test_client()

    response = client.get("/trigger-500")
    assert response.status_code == 500
    data = response.get_json()

    assert data["success"] is False
    assert data["status_code"] == 500
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred."
    assert "debug" not in data


def test_flask_internal_error_debug():
    set_settings(ErriumSettings(debug=True))

    app = create_test_app()
    client = app.test_client()

    response = client.get("/trigger-500")
    assert response.status_code == 500
    data = response.get_json()

    assert "debug" in data
    debug_info = data["debug"]
    assert debug_info["exception"] == "RuntimeError"
    assert debug_info["message"] == "Something went wrong internally"
    assert "RuntimeError: Something went wrong internally" in debug_info["stack_trace"]
