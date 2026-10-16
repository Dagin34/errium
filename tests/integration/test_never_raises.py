"""The error path must return the JSON envelope even for hostile exceptions."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask
from ninja import NinjaAPI
from ninja.testing import TestClient as NinjaTestClient
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from errium import ErriumMiddleware
from errium_core.config.settings import ErriumSettings, set_settings
from errium_flask import ErriumFlask
from errium_ninja import register_errium


class BadStr(Exception):
    def __str__(self) -> str:
        raise RuntimeError("str is broken")


class Unprintable:
    def __repr__(self) -> str:
        raise RuntimeError("cannot repr")

    __str__ = __repr__


def _hostile_exceptions() -> dict[str, Exception]:
    return {
        "bad_str": BadStr(),
        "unprintable_args": ValueError(Unprintable()),
        "huge_message": ValueError("x" * 500_000),
    }


@pytest.fixture(params=[False, True], ids=["prod", "debug"])
def debug(request: pytest.FixtureRequest) -> bool:
    set_settings(ErriumSettings(debug=request.param))
    return bool(request.param)


def _assert_envelope(data: dict, debug: bool, name: str) -> None:
    assert data["success"] is False
    assert data["status_code"] == 500
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["trace_id"]
    if debug:
        expected = {"bad_str": "BadStr", "unprintable_args": "ValueError"}
        assert data["debug"]["exception"] == expected.get(name, "ValueError")
        assert len(data["debug"]["message"]) <= 2000
    else:
        assert "debug" not in data


@pytest.mark.parametrize("name", list(_hostile_exceptions()))
def test_fastapi_never_raises(debug: bool, name: str) -> None:
    app = FastAPI()
    app.add_middleware(ErriumMiddleware)

    @app.get("/boom")
    def boom() -> None:
        raise _hostile_exceptions()[name]

    response = TestClient(app).get("/boom")
    assert response.status_code == 500
    _assert_envelope(response.json(), debug, name)


@pytest.mark.parametrize("name", list(_hostile_exceptions()))
def test_flask_never_raises(debug: bool, name: str) -> None:
    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/boom")
    def boom():  # type: ignore[no-untyped-def]
        raise _hostile_exceptions()[name]

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    _assert_envelope(response.get_json(), debug, name)


@pytest.mark.parametrize("name", list(_hostile_exceptions()))
def test_ninja_never_raises(debug: bool, name: str) -> None:
    api = NinjaAPI()
    register_errium(api)

    @api.get("/boom")
    def boom(request):  # type: ignore[no-untyped-def]
        raise _hostile_exceptions()[name]

    response = NinjaTestClient(api).get("/boom")
    assert response.status_code == 500
    _assert_envelope(response.json(), debug, name)


@pytest.mark.parametrize("name", list(_hostile_exceptions()))
def test_drf_never_raises(debug: bool, name: str) -> None:
    @api_view(["GET"])
    def boom(request: Request) -> Response:
        raise _hostile_exceptions()[name]

    response = boom(APIRequestFactory().get("/boom"))
    assert response.status_code == 500
    _assert_envelope(response.data, debug, name)
