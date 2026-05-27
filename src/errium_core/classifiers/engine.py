from errium_core.classifiers.generic import GenericExceptionClassifier
from errium_core.classifiers.validation import ValidationExceptionClassifier
from errium_core.contracts.classified_error import ClassifiedError


class ClassificationEngine:
    def __init__(self):
        self.classifiers = [
            ValidationExceptionClassifier(),
        ]

        self.fallback_classifier = GenericExceptionClassifier()

    def classify(self, exc: Exception) -> ClassifiedError:
        for classifier in self.classifiers:
            result = classifier.classify(exc)

            if result:
                return result

        return self.fallback_classifier.classify(exc)
