from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.generic import GenericExceptionClassifier
from errium_core.classifiers.validation import ValidationExceptionClassifier
from errium_core.contracts.classified_error import ClassifiedError


class ClassificationEngine:
    def __init__(self, classifiers: list[ExceptionClassifier] | None = None) -> None:
        """Initialize classification engine with default and optional classifiers."""
        self._classifiers: list[ExceptionClassifier] = []

        # Register default framework-agnostic validation classifier
        self.register(ValidationExceptionClassifier())

        if classifiers:
            for classifier in classifiers:
                self.register(classifier)

        self.fallback_classifier = GenericExceptionClassifier()

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

    def classify(self, exc: Exception) -> ClassifiedError:
        """Classify exception using registered classifiers or fallback."""
        for classifier in self._classifiers:
            result = classifier.classify(exc)
            if result is not None:
                return result

        return self.fallback_classifier.classify(exc)
