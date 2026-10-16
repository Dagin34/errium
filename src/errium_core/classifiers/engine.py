from errium_core import registry
from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.database import DatabaseExceptionClassifier
from errium_core.classifiers.generic import GenericExceptionClassifier
from errium_core.classifiers.validation import ValidationExceptionClassifier
from errium_core.contracts.classified_error import ClassifiedError


class ClassificationEngine:
    def __init__(self, classifiers: list[ExceptionClassifier] | None = None) -> None:
        """Initialize classification engine with default and optional classifiers."""
        self._classifiers: list[ExceptionClassifier] = []

        # Register default framework-agnostic classifiers
        self.register(ValidationExceptionClassifier())
        self.register(DatabaseExceptionClassifier())

        if classifiers:
            for classifier in classifiers:
                self.register(classifier)

        self.fallback_classifier = GenericExceptionClassifier()
        self._merged: list[ExceptionClassifier] = []
        self._merged_key: tuple[int, int] | None = None

    def register(self, classifier: ExceptionClassifier) -> None:
        """Register classifier and re-sort by priority (descending)."""
        self._classifiers.append(classifier)
        # Sort classifiers: highest priority first
        # (defaulting to 100 if priority is missing)
        self._classifiers.sort(key=lambda x: getattr(x, "priority", 100), reverse=True)

    @property
    def classifiers(self) -> list[ExceptionClassifier]:
        """Return the list of registered exception classifiers."""
        return self._classifiers

    def _active_classifiers(self) -> list[ExceptionClassifier]:
        """This engine's classifiers plus the process-wide registry, by priority."""
        shared = registry.registered_classifiers()
        if not shared:
            return self._classifiers
        key = (registry.registry_version(), len(self._classifiers))
        if key != self._merged_key:
            self._merged = sorted(
                [*self._classifiers, *shared],
                key=lambda x: getattr(x, "priority", 100),
                reverse=True,
            )
            self._merged_key = key
        return self._merged

    def classify(self, exc: Exception) -> ClassifiedError:
        """Classify exception using registered classifiers or fallback."""
        for classifier in self._active_classifiers():
            result = classifier.classify(exc)
            if result is not None:
                return result

        return self.fallback_classifier.classify(exc)
