from typing import Any, Protocol

from errium_core.contracts.error import StandardizedError


class ErrorFormatter(Protocol):
    def format(
        self,
        error: StandardizedError,
    ) -> dict[str, Any]: ...
