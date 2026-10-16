from flask import Flask, abort
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja.testing import TestClient as NinjaTestClient
from rest_framework.decorators import api_view
from rest_framework.exceptions import Throttled
from rest_framework.test import APIRequestFactory
from werkzeug.exceptions import MethodNotAllowed, TooManyRequests

from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.headers import protocol_headers
from errium_flask import ErriumFlask
from errium_ninja import register_errium


def flask_client():  # type: ignore[no-untyped-def]
    set_settings(ErriumSettings(debug=False))
    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/limited")
    def limited():  # type: ignore[no-untyped-def]
        raise TooManyRequests(retry_after=30)

    @app.get("/custom405")
    def custom_405():  # type: ignore[no-untyped-def]
        raise MethodNotAllowed(valid_methods=["GET", "HEAD"])

    @app.get("/teapot")
    def teapot():  # type: ignore[no-untyped-def]
        abort(418)

    return app.test_client()


def test_flask_keeps_retry_after() -> None:
    response = flask_client().get("/limited")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.get_json()["code"] == "RATE_LIMITED"


def test_flask_keeps_allow_on_explicit_and_routing_405() -> None:
    client = flask_client()
    assert client.get("/custom405").headers["Allow"] == "GET, HEAD"
    routed = client.post("/limited")
    assert routed.status_code == 405
    assert "GET" in routed.headers["Allow"]


def test_flask_does_not_copy_unrelated_headers() -> None:
    response = flask_client().get("/teapot")
    assert response.content_type == "application/json"


def test_ninja_keeps_headers_set_on_the_exception() -> None:
    class RateLimited(HttpError):
        headers = {"Retry-After": "7", "X-Secret": "nope"}

    api = NinjaAPI()
    register_errium(api)

    @api.get("/limited")
    def limited(request):  # type: ignore[no-untyped-def]
        raise RateLimited(429, "Slow down")

    response = NinjaTestClient(api).get("/limited")
    assert response._response["Retry-After"] == "7"
    assert not response._response.has_header("X-Secret")


def test_drf_throttled_keeps_retry_after() -> None:
    @api_view(["GET"])
    def limited(request):  # type: ignore[no-untyped-def]
        raise Throttled(wait=42)

    response = limited(APIRequestFactory().get("/x"))
    assert response["Retry-After"] == "42"


def test_protocol_headers_rejects_header_injection_and_never_raises() -> None:
    class Evil(Exception):
        headers = {"Retry-After": "1\r\nX-Injected: yes", "Allow": "GET"}

        def get_headers(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    assert protocol_headers(Evil()) == {"Allow": "GET"}
