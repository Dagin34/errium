import pytest
from django.test import Client, override_settings

from errium_core.config.settings import ErriumSettings, set_settings
from errium_django.negotiation import prefers_json

JSON = {"HTTP_ACCEPT": "application/json"}
HTML = {"HTTP_ACCEPT": "text/html,application/xhtml+xml,*/*;q=0.8"}
ENVELOPE = {
    "success",
    "status_code",
    "code",
    "message",
    "trace_id",
    "timestamp",
    "details",
}


@pytest.fixture(autouse=True)
def django_project():
    set_settings(ErriumSettings(debug=False))
    with override_settings(
        DEBUG=False,
        ROOT_URLCONF="django_urlconf",
        MIDDLEWARE=[
            "errium_django.ErriumDjangoMiddleware",
            "django_urlconf.BoomMiddleware",
        ],
    ):
        yield


@pytest.fixture
def client() -> Client:
    return Client(raise_request_exception=False)


def assert_envelope(response, status: int, code: str) -> dict:
    assert response.status_code == status
    assert response["Content-Type"].startswith("application/json")
    data = response.json()
    assert ENVELOPE <= set(data)
    assert data["status_code"] == status
    assert data["code"] == code
    assert response["X-Trace-Id"] == data["trace_id"]
    return data


@pytest.mark.parametrize(
    ("accept", "expected"),
    [
        ("application/json", True),
        ("application/json, text/plain, */*", True),
        ("application/problem+json", True),
        ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", False),
        ("text/html, application/json", False),
        ("text/html;q=0.5, application/json", True),
        ("*/*", False),
        ("application/json;q=0", False),
        ("", False),
    ],
)
def test_prefers_json(accept: str, expected: bool) -> None:
    assert prefers_json(accept) is expected


def test_unknown_url_json_vs_html(client: Client) -> None:
    data = assert_envelope(client.get("/nope/", **JSON), 404, "RESOURCE_NOT_FOUND")
    assert data["message"] == "Resource not found."  # no URL-pattern leak
    assert "tried" not in str(data)

    html = client.get("/nope/", **HTML)
    assert html.status_code == 404
    assert html["Content-Type"].startswith("text/html")


def test_api_prefix_gets_json_without_accept(client: Client) -> None:
    assert_envelope(client.get("/api/unknown"), 404, "RESOURCE_NOT_FOUND")


@override_settings(ERRIUM_JSON_PATH_PREFIXES=["/v2/"])
def test_json_path_prefixes_are_configurable(client: Client) -> None:
    assert client.get("/api/unknown")["Content-Type"].startswith("text/html")
    assert_envelope(client.get("/v2/unknown"), 404, "RESOURCE_NOT_FOUND")


def test_converter_mismatch(client: Client) -> None:
    assert_envelope(client.get("/item/abc/", **JSON), 404, "RESOURCE_NOT_FOUND")
    assert client.get("/item/7/", **JSON).json() == {"pk": 7}


def test_ninja_method_not_allowed_goes_through_the_formatter(client: Client) -> None:
    response = client.post("/api/ping")
    data = assert_envelope(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response["Allow"]
    assert data["message"] == "Method not allowed."


def test_middleware_exception_returns_envelope(client: Client) -> None:
    response = client.get("/plain/ok/", HTTP_X_BOOM="1", **JSON)
    data = assert_envelope(response, 500, "INTERNAL_SERVER_ERROR")
    assert data["message"] == "An unexpected error occurred."
    assert "middleware exploded" not in response.content.decode()


def test_middleware_exception_html_client_keeps_django_page(client: Client) -> None:
    response = client.get("/plain/ok/", HTTP_X_BOOM="1", **HTML)
    assert response.status_code == 500
    assert response["Content-Type"].startswith("text/html")


def test_plain_view_exceptions(client: Client) -> None:
    assert_envelope(client.get("/plain/boom/", **JSON), 500, "INTERNAL_SERVER_ERROR")
    assert_envelope(client.get("/plain/forbidden/", **JSON), 403, "AUTHORIZATION_ERROR")
    assert_envelope(client.get("/plain/suspicious/", **JSON), 400, "BAD_REQUEST")


def test_plain_view_html_client_keeps_django_page(client: Client) -> None:
    response = client.get("/plain/forbidden/", **HTML)
    assert response.status_code == 403
    assert response["Content-Type"].startswith("text/html")


def test_trace_id_exposed_on_request(client: Client) -> None:
    response = client.get("/nope/", **JSON)
    assert response.json()["trace_id"] == response["X-Trace-Id"]


def test_handler500_alone_covers_earlier_middleware() -> None:
    """Without the middleware, `handler500` still renders the envelope."""
    c = Client(raise_request_exception=False)
    with override_settings(MIDDLEWARE=["django_urlconf.BoomMiddleware"]):
        response = c.get("/plain/ok/", HTTP_X_BOOM="1", **JSON)
    assert_envelope(response, 500, "INTERNAL_SERVER_ERROR")
