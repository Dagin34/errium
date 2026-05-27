from dataclasses import dataclass


@dataclass(slots=True)
class ClassifiedError:
    category: str
    status_code: int
    message: str
