import logging

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from flask import Flask, g
from ninja import NinjaAPI
from ninja.testing import TestClient as NinjaTestClient
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

import errium
from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.tracing.trace import current_trace_id
from errium_flask import ErriumFlask
from errium_ninja import register_errium

GOOD_ID = "req-123.abc:DEF_9"


@pytest.fixture(autouse=True)
def prod() -> None:
    set_settings(ErriumSettings(debug=False))


def errium_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "errium"]


def assert_logged(caplog: pytest.LogCaptureFixture, trace_id: str, level: int) -> None:
    matching = [r for r in errium_records(caplog) if trace_id in r.getMessage()]
    assert len(matching) == 1
    record = matching[0]
    assert record.levelno == level
    assert record.errium_trace_id == trace_id  # type: ignore[attr-defined]
    if level >= logging.ERROR:
        assert record.exc_info is not None
    else:
        assert record.exc_info is None


def fastapi_app() -> FastAPI:
    app = FastAPI()
    errium.install(app)

    @app.get("/boom")
    def boom(request: Request) -> None:
        # The id is available to application code before anything fails.
        assert request.state.errium_trace_id == current_trace_id()
        raise RuntimeError("kaboom")

    @app.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="gone")

    return app


def test_fastapi_logs_500_with_traceback_and_trace_id(caplog) -> None:
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.WARNING, logger="errium"):
        response = client.get("/boom")
    body = response.json()
    assert response.headers["x-trace-id"] == body["trace_id"]
    assert_logged(caplog, body["trace_id"], logging.ERROR)
    record = errium_records(caplog)[0]
    assert "GET /boom -> 500 INTERNAL_SERVER_ERROR" in record.getMessage()
    assert isinstance(record.exc_info[1], RuntimeError)  # type: ignore[index]


def test_fastapi_logs_4xx_as_warning_without_traceback(caplog) -> None:
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.WARNING, logger="errium"):
        response = client.get("/missing")
    body = response.json()
    assert response.headers["x-trace-id"] == body["trace_id"]
    assert_logged(caplog, body["trace_id"], logging.WARNING)


def test_trace_id_is_fresh_uuid_by_default() -> None:
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    body = client.get("/boom", headers={"X-Request-ID": GOOD_ID}).json()
    assert body["trace_id"] != GOOD_ID
    assert len(body["trace_id"]) == 36


def test_trusted_request_id_is_reused() -> None:
    set_settings(ErriumSettings(debug=False, trust_request_id=True))
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    response = client.get("/boom", headers={"X-Request-ID": GOOD_ID})
    assert response.json()["trace_id"] == GOOD_ID
    assert response.headers["x-trace-id"] == GOOD_ID


@pytest.mark.parametrize("bad", ["x" * 129, "has space", "new\nline", "semi;colon"])
def test_unsafe_request_id_is_ignored(bad: str) -> None:
    set_settings(ErriumSettings(debug=False, trust_request_id=True))
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    try:
        response = client.get("/boom", headers={"X-Request-ID": bad})
    except Exception:  # the HTTP client itself may refuse a bad header
        return
    assert response.json()["trace_id"] != bad


def test_flask_logs_and_exposes_trace_id(caplog) -> None:
    app = Flask(__name__)
    ErriumFlask(app)
    seen: dict[str, str] = {}

    @app.get("/boom")
    def boom():  # type: ignore[no-untyped-def]
        seen["g"] = g.errium_trace_id
        seen["ctx"] = current_trace_id() or ""
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.WARNING, logger="errium"):
        response = app.test_client().get("/boom")
    body = response.get_json()
    assert response.headers["X-Trace-Id"] == body["trace_id"] == seen["g"]
    assert seen["ctx"] == body["trace_id"]
    assert_logged(caplog, body["trace_id"], logging.ERROR)


def test_flask_trusts_request_id_when_configured() -> None:
    set_settings(ErriumSettings(debug=False, trust_request_id=True))
    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/boom")
    def boom():  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    response = app.test_client().get("/boom", headers={"X-Request-ID": GOOD_ID})
    assert response.get_json()["trace_id"] == GOOD_ID


def test_ninja_logs_and_sets_header(caplog) -> None:
    api = NinjaAPI()
    register_errium(api)

    @api.get("/boom")
    def boom(request):  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.WARNING, logger="errium"):
        response = NinjaTestClient(api).get("/boom")
    body = response.json()
    assert response["X-Trace-Id"] == body["trace_id"]
    assert_logged(caplog, body["trace_id"], logging.ERROR)


def test_drf_logs_and_sets_header(caplog) -> None:
    @api_view(["GET"])
    def boom(request) -> Response:  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    @api_view(["GET"])
    def missing(request) -> Response:  # type: ignore[no-untyped-def]
        raise NotFound("nope")

    factory = APIRequestFactory()
    with caplog.at_level(logging.WARNING, logger="errium"):
        server_error = boom(factory.get("/boom"))
        client_error = missing(factory.get("/missing"))
    assert server_error["X-Trace-Id"] == server_error.data["trace_id"]
    assert_logged(caplog, server_error.data["trace_id"], logging.ERROR)
    assert_logged(caplog, client_error.data["trace_id"], logging.WARNING)


def test_drf_trusts_request_id_when_configured() -> None:
    set_settings(ErriumSettings(debug=False, trust_request_id=True))

    @api_view(["GET"])
    def boom(request) -> Response:  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    response = boom(APIRequestFactory().get("/boom", HTTP_X_REQUEST_ID=GOOD_ID))
    assert response.data["trace_id"] == GOOD_ID
    assert response["X-Trace-Id"] == GOOD_ID


def test_logging_failure_never_breaks_the_response(monkeypatch) -> None:
    import errium_core.pipeline as pipeline

    def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("logger broke")

    monkeypatch.setattr(pipeline.logger, "error", explode)
    client = TestClient(fastapi_app(), raise_server_exceptions=False)
    assert client.get("/boom").json()["code"] == "INTERNAL_SERVER_ERROR"
