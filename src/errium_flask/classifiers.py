from werkzeug.exceptions import HTTPException

from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.contracts.classified_error import ClassifiedError


class WerkzeugHTTPExceptionClassifier:
    @property
    def priority(self) -> int:
        """High priority for HTTP exceptions."""
        return 200

    def classify(self, exc: Exception) -> ClassifiedError | None:
        """Classify Werkzeug/Flask HTTPExceptions (raised via flask.abort, etc.)."""
        if not isinstance(exc, HTTPException):
            return None

        status_code = exc.code or 500
        category = category_for_status_code(status_code)

        message = exc.description or "An unexpected error occurred."

        return ClassifiedError(
            category=category,
            status_code=status_code,
            message=message,
        )
