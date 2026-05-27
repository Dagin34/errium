from typing import Protocol

from errium_core.contracts.classified_error import ClassifiedError


class ExceptionClassifier(Protocol):
    def classify(
        self,
        exc: Exception,
    ) -> ClassifiedError | None: ...
