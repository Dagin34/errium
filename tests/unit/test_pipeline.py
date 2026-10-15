from errium_core.classifiers.engine import ClassificationEngine
from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.formatters.default import DefaultFormatter
from errium_core.pipeline import handle_error


class BadStr(Exception):
    def __str__(self) -> str:
        raise RuntimeError("str is broken")


class ExplodingEngine(ClassificationEngine):
    def classify(self, exc):  # type: ignore[no-untyped-def]
        raise RuntimeError("classifier blew up")


def test_bad_str_exception_in_debug_keeps_real_class_name():
    set_settings(ErriumSettings(debug=True))
    handled = handle_error(
        BadStr(), engine=ClassificationEngine(), formatter=DefaultFormatter()
    )
    assert handled.status_code == 500
    assert handled.body["debug"]["exception"] == "BadStr"


def test_failing_engine_returns_generic_envelope():
    set_settings(ErriumSettings(debug=False))
    handled = handle_error(
        ValueError("x"), engine=ExplodingEngine(), formatter=DefaultFormatter()
    )
    assert handled.status_code == 500
    assert handled.body["code"] == "INTERNAL_SERVER_ERROR"
    assert handled.body["success"] is False
    assert handled.body["trace_id"]
    assert "debug" not in handled.body


def test_failing_details_callable_returns_generic_envelope():
    set_settings(ErriumSettings(debug=False))

    def boom() -> dict[str, str]:
        raise RuntimeError("normalizer blew up")

    handled = handle_error(
        ValueError("x"),
        engine=ClassificationEngine(),
        formatter=DefaultFormatter(),
        details=boom,
    )
    assert handled.status_code == 500
    assert handled.body["code"] == "INTERNAL_SERVER_ERROR"
