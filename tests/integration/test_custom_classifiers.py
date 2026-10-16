import pytest
from custom_classifier_support import QuotaClassifier, QuotaExceeded
from django.test import override_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask
from ninja import NinjaAPI
from ninja.testing import TestClient as NinjaTestClient
from rest_framework.decorators import api_view
from rest_framework.test import APIRequestFactory

import errium
import errium_drf.handler as drf_handler
from errium import ErriumMiddleware
from errium_core import registry
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.config.settings import ErriumSettings, set_settings
from errium_drf import make_exception_handler
from errium_flask import ErriumFlask
from errium_ninja import register_errium


@pytest.fixture(autouse=True)
def clean() -> None:
    set_settings(ErriumSettings(debug=False))
    registry.clear_registry()
    drf_handler._default_engine = None
    yield
    registry.clear_registry()
    drf_handler._default_engine = None


def assert_quota(status: int, code: str, message: str, data: dict) -> None:
    assert data["status_code"] == status
    assert data["code"] == code
    assert data["message"] == message


def test_fastapi_middleware_kwarg_route() -> None:
    app = FastAPI()
    app.add_middleware(ErriumMiddleware, classifiers=[QuotaClassifier()])

    @app.get("/q")
    def q() -> None:
        raise QuotaExceeded

    response = TestClient(app).get("/q")
    assert response.status_code == 409
    assert_quota(409, "CONFLICT", "Quota already in use.", response.json())


def test_fastapi_install_classifiers_reach_every_entry_point() -> None:
    from fastapi import HTTPException

    class Teapot(QuotaClassifier):
        @property
        def priority(self) -> int:
            return 250  # above FastAPIHTTPExceptionClassifier (200)

        def classify(self, exc):  # type: ignore[no-untyped-def]
            if isinstance(exc, HTTPException) and exc.status_code == 418:
                from errium_core.contracts.classified_error import ClassifiedError

                return ClassifiedError("TEAPOT", 418, "I am a teapot")
            return super().classify(exc)

    app = FastAPI()
    errium.install(app, classifiers=[Teapot()])

    @app.get("/q")
    def q() -> None:
        raise QuotaExceeded

    @app.get("/t")
    def t() -> None:
        raise HTTPException(status_code=418, detail="x")

    client = TestClient(app)
    assert_quota(409, "CONFLICT", "Quota already in use.", client.get("/q").json())
    # The HTTPException *handler* (not the middleware) used the custom classifier.
    assert client.get("/t").json()["code"] == "TEAPOT"


def test_fastapi_legacy_manual_setup_shares_middleware_engine() -> None:
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException

    from errium.handlers.http_handler import http_exception_handler
    from errium.handlers.validation_handler import validation_exception_handler

    app = FastAPI()
    app.add_middleware(ErriumMiddleware, classifiers=[QuotaClassifier()])
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    assert TestClient(app).get("/nope").json()["code"] == "RESOURCE_NOT_FOUND"


def test_fastapi_engine_param_replaces_default_engine() -> None:
    app = FastAPI()
    app.add_middleware(
        ErriumMiddleware, engine=ClassificationEngine([QuotaClassifier()])
    )

    @app.get("/q")
    def q() -> None:
        raise QuotaExceeded

    assert TestClient(app).get("/q").json()["code"] == "CONFLICT"


def test_flask_classifiers_and_engine() -> None:
    app = Flask(__name__)
    ErriumFlask(app, classifiers=[QuotaClassifier()])

    @app.get("/q")
    def q():  # type: ignore[no-untyped-def]
        raise QuotaExceeded

    response = app.test_client().get("/q")
    assert_quota(409, "CONFLICT", "Quota already in use.", response.get_json())

    second = Flask(__name__)
    ErriumFlask().init_app(second)  # old call forms keep working
    second.get("/q")(q)
    assert second.test_client().get("/q").status_code == 500


def test_ninja_classifiers() -> None:
    api = NinjaAPI(urls_namespace="t8")
    register_errium(api, classifiers=[QuotaClassifier()])

    @api.get("/q")
    def q(request):  # type: ignore[no-untyped-def]
        raise QuotaExceeded

    response = NinjaTestClient(api).get("/q")
    assert_quota(409, "CONFLICT", "Quota already in use.", response.json())


def drf_view():  # type: ignore[no-untyped-def]
    @api_view(["GET"])
    def view(request):  # type: ignore[no-untyped-def]
        raise QuotaExceeded

    return view


def test_drf_make_exception_handler() -> None:
    handler = make_exception_handler(classifiers=[QuotaClassifier()])
    view = drf_view()
    view.cls.get_exception_handler = lambda self: handler  # type: ignore[attr-defined]
    response = view(APIRequestFactory().get("/q"))
    assert_quota(409, "CONFLICT", "Quota already in use.", response.data)


def test_drf_settings_classifiers() -> None:
    with override_settings(
        ERRIUM={"CLASSIFIERS": ["custom_classifier_support.QuotaClassifier"]}
    ):
        response = drf_view()(APIRequestFactory().get("/q"))
    assert_quota(409, "CONFLICT", "Quota already in use.", response.data)


def test_register_function_form_applies_to_every_adapter() -> None:
    errium.register(QuotaExceeded, status=429, message="Quota exceeded, retry later.")

    app = Flask(__name__)
    ErriumFlask(app)
    app.get("/q")(lambda: (_ for _ in ()).throw(QuotaExceeded()))
    flask_data = app.test_client().get("/q").get_json()
    assert_quota(429, "RATE_LIMITED", "Quota exceeded, retry later.", flask_data)

    fast = FastAPI()
    errium.install(fast)

    @fast.get("/q")
    def q() -> None:
        raise QuotaExceeded

    assert TestClient(fast).get("/q").json()["code"] == "RATE_LIMITED"
    assert drf_view()(APIRequestFactory().get("/q")).data["code"] == "RATE_LIMITED"


def test_register_decorator_form_with_category_and_callable_message() -> None:
    @errium.register(
        status=402, category="PAYMENT_REQUIRED", message=lambda e: f"Pay up: {e}"
    )
    class PaymentNeeded(Exception):
        pass

    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/p")
    def p():  # type: ignore[no-untyped-def]
        raise PaymentNeeded("invoice 7")

    data = app.test_client().get("/p").get_json()
    assert_quota(402, "PAYMENT_REQUIRED", "Pay up: invoice 7", data)


def test_register_defaults_to_exception_text_and_matches_subclasses() -> None:
    class Base(Exception):
        pass

    class Child(Base):
        pass

    errium.register(Base, status=409)
    app = Flask(__name__)
    ErriumFlask(app)

    @app.get("/c")
    def c():  # type: ignore[no-untyped-def]
        raise Child("already there")

    data = app.test_client().get("/c").get_json()
    assert_quota(409, "CONFLICT", "already there", data)


def test_registered_5xx_is_still_sanitized_in_production() -> None:
    errium.register(QuotaExceeded, status=503, message="internal detail")
    app = Flask(__name__)
    ErriumFlask(app)
    app.get("/q")(lambda: (_ for _ in ()).throw(QuotaExceeded()))
    data = app.test_client().get("/q").get_json()
    assert data["code"] == "SERVICE_UNAVAILABLE"
    assert "internal detail" not in data["message"]


def test_priority_rules_unchanged() -> None:
    class Low(QuotaClassifier):
        @property
        def priority(self) -> int:
            return 1

        def classify(self, exc):  # type: ignore[no-untyped-def]
            from errium_core.contracts.classified_error import ClassifiedError

            return (
                ClassifiedError("LOW", 418, "low")
                if isinstance(exc, QuotaExceeded)
                else None
            )

    engine = ClassificationEngine([Low(), QuotaClassifier()])
    assert engine.classify(QuotaExceeded()).category == "CONFLICT"
