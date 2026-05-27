from typing import Protocol

from errium_core.contracts.classified_error import ClassifiedError


class ExceptionClassifier(Protocol):
    @property
    def priority(self) -> int:
        """The evaluation priority of this classifier.

        Higher priorities are evaluated first.
        """
        ...

    def classify(
        self,
        exc: Exception,
    ) -> ClassifiedError | None: ...
