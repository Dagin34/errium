from typing import Protocol

from errium_core.contracts.error import StandardizedError


class ErrorFormatter(Protocol):
    def format(
        self,
        error: StandardizedError,
    ) -> dict: ...
