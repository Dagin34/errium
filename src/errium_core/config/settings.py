import os
from dataclasses import dataclass

_TRUE_VALUES = ("true", "1", "yes", "on")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in _TRUE_VALUES


@dataclass
class ErriumSettings:
    debug: bool = False
    # Reuse a valid inbound X-Request-ID as the trace_id (ERRIUM_TRUST_REQUEST_ID).
    trust_request_id: bool = False


# Instantiate global settings from the ERRIUM_DEBUG / ERRIUM_TRUST_REQUEST_ID
# environment variables
_settings = ErriumSettings(
    debug=os.getenv("ERRIUM_DEBUG", "false").lower() in ("true", "1", "yes"),
    trust_request_id=_env_flag("ERRIUM_TRUST_REQUEST_ID"),
)


def get_settings() -> ErriumSettings:
    """Get the current global Errium settings."""
    return _settings


def set_settings(settings: ErriumSettings) -> None:
    """Dynamically set the global Errium settings (useful for testing)."""
    global _settings
    _settings = settings
