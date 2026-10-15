import logging

import pytest

import errium
import errium_core
import errium_django
import errium_drf
import errium_flask
import errium_ninja
from errium_core.config.settings import announce_mode, load_settings


def test_every_package_exposes_the_same_version() -> None:
    versions = {
        errium.__version__,
        errium_core.__version__,
        errium_flask.__version__,
        errium_ninja.__version__,
        errium_drf.__version__,
        errium_django.__version__,
    }
    assert len(versions) == 1
    assert versions.pop() != "0+unknown"


@pytest.mark.parametrize(
    "value",
    ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON", " true", "true ", " on "],
)
def test_debug_enabling_values(value: str) -> None:
    assert load_settings({"ERRIUM_DEBUG": value}).debug is True


@pytest.mark.parametrize(
    "value", ["", "false", "0", "no", "off", "y", "t", "enabled", "debug", "2"]
)
def test_other_values_stay_off(value: str) -> None:
    assert load_settings({"ERRIUM_DEBUG": value}).debug is False


def test_debug_defaults_off() -> None:
    settings = load_settings({})
    assert settings.debug is False
    assert settings.trust_request_id is False


def test_trust_request_id_flag() -> None:
    assert load_settings({"ERRIUM_TRUST_REQUEST_ID": "On"}).trust_request_id is True


def test_announce_mode_logs_one_info_line(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="errium"):
        announce_mode(load_settings({}), {})
    messages = [r for r in caplog.records if r.name == "errium"]
    assert len(messages) == 1
    assert messages[0].levelno == logging.INFO
    assert "off" in messages[0].getMessage()


def test_announce_mode_warns_when_debug_looks_like_production(
    caplog: pytest.LogCaptureFixture,
) -> None:
    environ = {"ERRIUM_DEBUG": "on", "ERRIUM_ENV": "Production"}
    with caplog.at_level(logging.INFO, logger="errium"):
        announce_mode(load_settings(environ), environ)
    levels = [r.levelno for r in caplog.records if r.name == "errium"]
    assert logging.WARNING in levels


def test_announce_mode_no_warning_in_development(
    caplog: pytest.LogCaptureFixture,
) -> None:
    environ = {"ERRIUM_DEBUG": "true", "ERRIUM_ENV": "development"}
    with caplog.at_level(logging.INFO, logger="errium"):
        announce_mode(load_settings(environ), environ)
    assert logging.WARNING not in [r.levelno for r in caplog.records]
