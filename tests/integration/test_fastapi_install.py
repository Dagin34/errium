import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

import errium
from errium_core.config.settings import ErriumSettings, set_settings

ENVELOPE_KEYS = {
    "success",
    "status_code",
    "code",
    "message",
    "trace_id",
    "timestamp",
    "details",
}


class Item(BaseModel):
    name: str


def forbidden_dependency() -> None:
    raise HTTPException(status_code=403, detail="Nope")


def make_app() -> FastAPI:
    app = FastAPI()
    errium.install(app)

    @app.get("/http/{code}")
    def raise_http(code: int, msg: str = "custom message") -> None:
        raise HTTPException(status_code=code, detail=msg)

    @app.get("/headers")
    def with_headers() -> None:
        raise HTTPException(
            status_code=429,
            detail="Slow down",
            headers={"Retry-After": "30", "X-A": "1", "WWW-Authenticate": "Bearer"},
        )

    @app.get("/starlette-418")
    def teapot() -> None:
        raise StarletteHTTPException(status_code=418, detail="teapot")

    @app.get("/dict-detail")
    def dict_detail() -> None:
        raise HTTPException(status_code=400, detail={"field": "bad", "n": 1})

    @app.get("/list-detail")
    def list_detail() -> None:
        raise HTTPException(status_code=400, detail=["a", "b"])

    @app.get("/dep", dependencies=[Depends(forbidden_dependency)])
    def dep() -> dict:
        return {}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    @app.get("/ok")
    def ok() -> dict:
        return {"ok": True}

    @app.post("/items")
    def create(item: Item) -> dict:
        return item.model_dump()

    return app


@pytest.fixture(autouse=True)
def prod() -> None:
    set_settings(ErriumSettings(debug=False))


@pytest.fixture
def client() -> TestClient:
    return TestClient(make_app(), raise_server_exceptions=False)


def assert_envelope(response, status: int, code: str) -> dict:
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert ENVELOPE_KEYS <= set(data)
    assert data["status_code"] == status == response.status_code
    assert data["code"] == code
    return data


def test_http_exception_is_normalised(client: TestClient) -> None:
    data = assert_envelope(client.get("/http/404"), 404, "RESOURCE_NOT_FOUND")
    assert data["message"] == "custom message"
    assert "detail" not in data


def test_http_500_private_message_does_not_leak(client: TestClient) -> None:
    response = client.get("/http/500", params={"msg": "SECRET-INTERNAL-DETAIL"})
    data = assert_envelope(response, 500, "INTERNAL_SERVER_ERROR")
    assert "SECRET-INTERNAL-DETAIL" not in response.text
    assert data["message"] == "An unexpected error occurred."


def test_routing_404_and_405(client: TestClient) -> None:
    assert_envelope(client.get("/nope"), 404, "RESOURCE_NOT_FOUND")
    response = client.post("/ok")
    assert_envelope(response, 405, "METHOD_NOT_ALLOWED")
    assert "allow" in response.headers


def test_headers_survive(client: TestClient) -> None:
    response = client.get("/headers")
    assert_envelope(response, 429, "RATE_LIMITED")
    assert response.headers["retry-after"] == "30"
    assert response.headers["x-a"] == "1"
    assert response.headers["www-authenticate"] == "Bearer"


def test_starlette_http_exception(client: TestClient) -> None:
    assert_envelope(client.get("/starlette-418"), 418, "BAD_REQUEST")


def test_dict_and_list_detail_become_details(client: TestClient) -> None:
    data = assert_envelope(client.get("/dict-detail"), 400, "BAD_REQUEST")
    assert data["message"] == "Bad Request"
    assert data["details"] == {"field": "bad", "n": "1"}

    data = assert_envelope(client.get("/list-detail"), 400, "BAD_REQUEST")
    assert data["details"] == {"0": "a", "1": "b"}


def test_dependency_http_exception(client: TestClient) -> None:
    assert_envelope(client.get("/dep"), 403, "AUTHORIZATION_ERROR")


def test_uncaught_exception_still_handled(client: TestClient) -> None:
    assert_envelope(client.get("/boom"), 500, "INTERNAL_SERVER_ERROR")


def test_invalid_utf8_body_is_normalised(client: TestClient) -> None:
    response = client.post(
        "/items", content=b"\xff\xfe", headers={"content-type": "application/json"}
    )
    assert_envelope(response, 400, "BAD_REQUEST")


def test_install_is_idempotent() -> None:
    app = FastAPI()
    errium.install(app)
    errium.install(app)
    assert len(app.user_middleware) == 1


def test_install_debug_override() -> None:
    app = FastAPI()
    errium.install(app, debug=True)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    data = TestClient(app).get("/boom").json()
    assert data["debug"]["exception"] == "RuntimeError"


def test_mounted_sub_app_needs_its_own_install() -> None:
    parent = FastAPI()
    errium.install(parent)
    sub = FastAPI()
    errium.install(sub)

    @sub.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    @sub.get("/http")
    def http() -> None:
        raise HTTPException(status_code=409, detail="Clash")

    parent.mount("/sub", sub)
    client = TestClient(parent, raise_server_exceptions=False)
    assert_envelope(client.get("/sub/boom"), 500, "INTERNAL_SERVER_ERROR")
    assert_envelope(client.get("/sub/http"), 409, "CONFLICT")
    assert_envelope(client.get("/sub/missing"), 404, "RESOURCE_NOT_FOUND")


def test_legacy_two_line_setup_still_works() -> None:
    from fastapi.exceptions import RequestValidationError

    from errium import ErriumMiddleware
    from errium.handlers.validation_handler import validation_exception_handler

    app = FastAPI()
    app.add_middleware(ErriumMiddleware)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    @app.post("/items")
    def create(item: Item) -> dict:
        return item.model_dump()

    client = TestClient(app, raise_server_exceptions=False)
    assert_envelope(client.get("/boom"), 500, "INTERNAL_SERVER_ERROR")
    assert_envelope(client.post("/items", json={}), 422, "VALIDATION_ERROR")
