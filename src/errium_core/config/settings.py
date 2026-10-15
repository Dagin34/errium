import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

logger = logging.getLogger("errium")

_TRUE_VALUES = ("true", "1", "yes", "on")

# Environment names that signal "this is production" for the debug-mode warning.
_ENV_VARIABLES = ("ERRIUM_ENV", "APP_ENV", "ENVIRONMENT", "ENV")
_PRODUCTION_VALUES = ("production", "prod", "live")


def _env_flag(environ: Mapping[str, str], name: str) -> bool:
    """True for `true`/`1`/`yes`/`on` (case-insensitive, surrounding spaces ignored)."""
    return environ.get(name, "").strip().lower() in _TRUE_VALUES


@dataclass
class ErriumSettings:
    debug: bool = False
    # Reuse a valid inbound X-Request-ID as the trace_id (ERRIUM_TRUST_REQUEST_ID).
    trust_request_id: bool = False


def load_settings(environ: Mapping[str, str] | None = None) -> ErriumSettings:
    """Build settings from `ERRIUM_DEBUG` / `ERRIUM_TRUST_REQUEST_ID`."""
    environ = os.environ if environ is None else environ
    return ErriumSettings(
        debug=_env_flag(environ, "ERRIUM_DEBUG"),
        trust_request_id=_env_flag(environ, "ERRIUM_TRUST_REQUEST_ID"),
    )


def announce_mode(
    settings: ErriumSettings, environ: Mapping[str, str] | None = None
) -> None:
    """Log the active mode once (INFO), and warn if debug looks like production."""
    environ = os.environ if environ is None else environ
    logger.info(
        "Errium debug mode is %s (set ERRIUM_DEBUG=true to enable).",
        "ON" if settings.debug else "off",
    )
    if settings.debug:
        for name in _ENV_VARIABLES:
            if environ.get(name, "").strip().lower() in _PRODUCTION_VALUES:
                logger.warning(
                    "Errium debug mode is ON while %s=%s: error responses include "
                    "exception details and stack traces. Unset ERRIUM_DEBUG in "
                    "production.",
                    name,
                    environ[name],
                )
                break


# Instantiate global settings from the environment
_settings = load_settings()
announce_mode(_settings)


def get_settings() -> ErriumSettings:
    """Get the current global Errium settings."""
    return _settings


def set_settings(settings: ErriumSettings) -> None:
    """Dynamically set the global Errium settings (useful for testing)."""
    global _settings
    _settings = settings
