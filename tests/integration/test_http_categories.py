"""Status -> category consistency and the malformed-JSON decision (400)."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from flask import Flask, abort, request
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.testing import TestClient as NinjaTestClient
from pydantic import BaseModel
from rest_framework.decorators import api_view
from rest_framework.exceptions import MethodNotAllowed, ParseError, Throttled
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from errium import ErriumMiddleware
from errium.handlers.validation_handler import validation_exception_handler
from errium_core.config.settings import ErriumSettings, set_settings
from errium_flask import ErriumFlask
from errium_ninja import register_errium


class Item(BaseModel):
    name: str


def test_fastapi_malformed_json_is_400_bad_request() -> None:
    set_settings(ErriumSettings(debug=False))
    app = FastAPI()
    app.add_middleware(ErriumMiddleware)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.post("/items")
    def create(item: Item) -> dict:
        return item.model_dump()

    client = TestClient(app)
    response = client.post(
        "/items", content="{not json", headers={"content-type": "application/json"}
    )
    data = response.json()
    assert response.status_code == 400
    assert data["code"] == "BAD_REQUEST"
    assert data["message"] == "Malformed request body."
    assert data["details"] is None

    # Schema errors stay 422 VALIDATION_ERROR.
    schema_error = client.post("/items", json={})
    assert schema_error.status_code == 422
    assert schema_error.json()["code"] == "VALIDATION_ERROR"


def test_flask_http_statuses_get_matching_codes() -> None:
    set_settings(ErriumSettings(debug=False))
    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/status/<int:code>")
    def status(code: int):  # type: ignore[no-untyped-def]
        abort(code)

    @app.post("/items")
    def create():  # type: ignore[no-untyped-def]
        return Item.model_validate(request.get_json()).model_dump()

    client = app.test_client()
    expected = {
        408: "TIMEOUT",
        410: "GONE",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        429: "RATE_LIMITED",
        451: "BAD_REQUEST",
        503: "SERVICE_UNAVAILABLE",
    }
    for code, category in expected.items():
        data = client.get(f"/status/{code}").get_json()
        assert data["status_code"] == code
        assert data["code"] == category, code

    assert client.post("/status/404").get_json()["code"] == "METHOD_NOT_ALLOWED"

    malformed = client.post(
        "/items", data="{nope", headers={"content-type": "application/json"}
    )
    assert malformed.status_code == 400
    assert malformed.get_json()["code"] == "BAD_REQUEST"


class Payload(Schema):
    name: str


def test_ninja_http_error_codes() -> None:
    set_settings(ErriumSettings(debug=False))
    api = NinjaAPI()
    register_errium(api)

    @api.get("/limited")
    def limited(request):  # type: ignore[no-untyped-def]
        raise HttpError(429, "Slow down")

    @api.post("/items")
    def create(request, payload: Payload):  # type: ignore[no-untyped-def]
        return payload.dict()

    client = NinjaTestClient(api)
    data = client.get("/limited").json()
    assert (data["status_code"], data["code"]) == (429, "RATE_LIMITED")

    malformed = client.post("/items", data="{nope", content_type="application/json")
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "BAD_REQUEST"


def test_drf_exception_codes() -> None:
    set_settings(ErriumSettings(debug=False))
    factory = APIRequestFactory()

    def view_raising(exc: Exception):  # type: ignore[no-untyped-def]
        @api_view(["GET"])
        def view(request: Request) -> Response:
            raise exc

        return view

    cases = [
        (Throttled(wait=3), 429, "RATE_LIMITED"),
        (ParseError("bad"), 400, "BAD_REQUEST"),
        (MethodNotAllowed("POST"), 405, "METHOD_NOT_ALLOWED"),
    ]
    for exc, status, category in cases:
        response = view_raising(exc)(factory.get("/x"))
        assert response.status_code == status
        assert response.data["code"] == category
