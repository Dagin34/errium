from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.classified_error import ClassifiedError


class Resolver404Classifier:
    @property
    def priority(self) -> int:
        """Above DjangoExceptionClassifier, which would echo the message."""
        return 195

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Django's `Resolver404` message lists every URL pattern it tried.

        That is useful in a debug page but should not reach an API client, so
        an unmatched URL gets a fixed message.
        """
        if not any(klass.__name__ == "Resolver404" for klass in type(exc).__mro__):
            return None

        return ClassifiedError(
            category=ErrorCategory.NOT_FOUND,
            status_code=404,
            message="Resource not found.",
        )
