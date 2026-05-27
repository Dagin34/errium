from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class StandardizedError:
    status_code: int
    code: str
    message: str
    trace_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] | None = None
