import os
from dataclasses import dataclass


@dataclass
class ErriumSettings:
    debug: bool = False


# Instantiate global settings based on ERRIUM_DEBUG environment variable
_settings = ErriumSettings(
    debug=os.getenv("ERRIUM_DEBUG", "false").lower() in ("true", "1", "yes")
)


def get_settings() -> ErriumSettings:
    """Get the current global Errium settings."""
    return _settings


def set_settings(settings: ErriumSettings) -> None:
    """Dynamically set the global Errium settings (useful for testing)."""
    global _settings
    _settings = settings
