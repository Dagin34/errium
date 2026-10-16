import pytest

from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (400, "BAD_REQUEST"),
        (401, "AUTHENTICATION_ERROR"),
        (403, "AUTHORIZATION_ERROR"),
        (404, "RESOURCE_NOT_FOUND"),
        (405, "METHOD_NOT_ALLOWED"),
        (406, "NOT_ACCEPTABLE"),
        (408, "TIMEOUT"),
        (409, "CONFLICT"),
        (410, "GONE"),
        (413, "PAYLOAD_TOO_LARGE"),
        (415, "UNSUPPORTED_MEDIA_TYPE"),
        (418, "BAD_REQUEST"),
        (422, "VALIDATION_ERROR"),
        (423, "BAD_REQUEST"),
        (429, "RATE_LIMITED"),
        (451, "BAD_REQUEST"),
        (500, "INTERNAL_SERVER_ERROR"),
        (501, "INTERNAL_SERVER_ERROR"),
        (502, "SERVICE_UNAVAILABLE"),
        (503, "SERVICE_UNAVAILABLE"),
        (504, "TIMEOUT"),
        (599, "INTERNAL_SERVER_ERROR"),
    ],
)
def test_status_to_category(status: int, category: str) -> None:
    assert category_for_status_code(status) == category


def _format(status: int, code: str, message: str = "secret detail") -> dict:
    return DefaultFormatter().format(
        StandardizedError(
            status_code=status,
            code=code,
            message=message,
            trace_id="t",
            details={"leak": "x"},
        )
    )


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (502, "SERVICE_UNAVAILABLE"),
        (503, "SERVICE_UNAVAILABLE"),
        (504, "TIMEOUT"),
    ],
)
def test_prod_keeps_category_for_gateway_errors(status: int, code: str) -> None:
    set_settings(ErriumSettings(debug=False))
    body = _format(status, code)
    assert body["code"] == code
    assert body["message"] != "secret detail"
    assert body["details"] is None


@pytest.mark.parametrize("status", [500, 501, 505, 599])
def test_prod_collapses_other_5xx(status: int) -> None:
    set_settings(ErriumSettings(debug=False))
    body = _format(status, ErrorCategory.DATABASE.value)
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["message"] == "An unexpected error occurred."
    assert body["details"] is None


def test_debug_keeps_exact_5xx_code_and_message() -> None:
    set_settings(ErriumSettings(debug=True))
    body = _format(503, "SERVICE_UNAVAILABLE", "db is down")
    assert body["code"] == "SERVICE_UNAVAILABLE"
    assert body["message"] == "db is down"


def test_4xx_message_is_never_sanitized() -> None:
    set_settings(ErriumSettings(debug=False))
    body = _format(429, "RATE_LIMITED", "Slow down")
    assert body["code"] == "RATE_LIMITED"
    assert body["message"] == "Slow down"
