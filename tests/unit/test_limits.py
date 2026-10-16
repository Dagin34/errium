from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from rest_framework.exceptions import ErrorDetail

import errium
from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.limits import cap_details
from errium_drf.normalizers import flatten_drf_errors


def test_cap_details_under_limit_has_no_sentinel() -> None:
    details = {f"f{i}": "bad" for i in range(50)}
    assert cap_details(details) == details


def test_cap_details_over_limit_adds_sentinel() -> None:
    capped = cap_details({f"f{i}": "bad" for i in range(600)})
    assert capped is not None
    assert len(capped) == 51
    assert capped["_truncated"] == "550 more"
    assert "f0" in capped and "f49" in capped and "f50" not in capped


def test_cap_details_truncates_long_values_and_keys() -> None:
    capped = cap_details({"k" * 1000: "v" * 10_000})
    assert capped is not None
    ((key, value),) = capped.items()
    assert len(key) == 200
    assert len(value) == 500


def test_cap_details_none() -> None:
    assert cap_details(None) is None


def test_formatter_caps_details_in_prod() -> None:
    set_settings(ErriumSettings(debug=False))
    body = DefaultFormatter().format(
        StandardizedError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Validation failed.",
            trace_id="t",
            details={f"item.{i}.name": "Field required." for i in range(200)},
        )
    )
    assert len(body["details"]) == 51
    assert len(str(body)) < 25_000


def test_debug_message_and_stack_trace_are_capped() -> None:
    set_settings(ErriumSettings(debug=True))
    try:
        raise ValueError("x" * 400_000)
    except ValueError as exc:
        body = DefaultFormatter().format(
            StandardizedError(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="m",
                trace_id="t",
                exception=exc,
            )
        )
    assert len(body["debug"]["message"]) <= 2000
    assert len(body["debug"]["stack_trace"]) <= 20_000
    assert len(str(body)) < 30_000


def test_fastapi_debug_does_not_echo_request_input() -> None:
    set_settings(ErriumSettings(debug=True))

    class Login(BaseModel):
        username: str
        password: str

    app = FastAPI()
    errium.install(app)

    @app.post("/login")
    def login(body: Login) -> dict:
        return {}

    secret = "hunter2-SECRET"
    response = TestClient(app).post("/login", json={"username": 5, "password": secret})
    text = response.text
    assert response.status_code == 422
    assert secret not in text
    assert "'input'" not in text
    debug = response.json()["debug"]
    assert "username" in debug["message"]
    assert "string_type" in debug["message"] or "valid string" in debug["message"]
    assert "username" in debug["stack_trace"]


def test_fastapi_debug_huge_request_is_bounded() -> None:
    set_settings(ErriumSettings(debug=True))

    class Doc(BaseModel):
        text: int

    app = FastAPI()
    errium.install(app)

    @app.post("/doc")
    def doc(body: Doc) -> dict:
        return {}

    response = TestClient(app).post("/doc", json={"text": "x" * 1_000_000})
    assert response.status_code == 422
    assert len(response.content) < 30_000


def test_drf_non_field_errors_key_and_joining() -> None:
    detail = {
        "non_field_errors": [ErrorDetail("Passwords differ.")],
        "address": {"non_field_errors": [ErrorDetail("Bad address.")]},
        "password": [ErrorDetail("Too short."), ErrorDetail("Digits only.")],
    }
    assert flatten_drf_errors(detail) == {
        "_": "Passwords differ.",
        "address._": "Bad address.",
        "password": "Too short.; Digits only.",
    }
