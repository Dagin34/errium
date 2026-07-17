from flask import Flask, jsonify
from flask.typing import ResponseReturnValue
from pydantic import ValidationError as PydanticValidationError

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.tracing.trace import generate_trace_id
from errium_flask.classifiers import WerkzeugHTTPExceptionClassifier


class ErriumFlask:
    """Errium extension for Flask.

    Usage:
        app = Flask(__name__)
        ErriumFlask(app)

    or, using the app factory pattern:
        errium = ErriumFlask()
        errium.init_app(app)
    """

    def __init__(self, app: Flask | None = None) -> None:
        self.classification_engine = ClassificationEngine()
        # Register Flask/Werkzeug classifier for high-priority handling
        self.classification_engine.register(WerkzeugHTTPExceptionClassifier())

        self.formatter = DefaultFormatter()
        self.normalizer = ValidationNormalizer()

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Register the catch-all error handler on the given Flask app.

        Registering on the base `Exception` class is sufficient: Flask
        dispatches both raised HTTPExceptions (e.g. via `flask.abort`) and
        unhandled generic exceptions to it when no more specific handler
        is registered.
        """
        app.register_error_handler(Exception, self._handle_exception)

    def _handle_exception(self, exc: Exception) -> ResponseReturnValue:
        trace_id = generate_trace_id()

        classified = self.classification_engine.classify(exc)

        # Beautify raw pydantic validation errors into a flat field->message dict,
        # mirroring the FastAPI adapter's RequestValidationError handling.
        details = None
        if isinstance(exc, PydanticValidationError):
            details = self.normalizer.normalize(exc.errors())

        error = StandardizedError(
            status_code=classified.status_code,
            code=classified.category,
            message=classified.message,
            trace_id=trace_id,
            success=False,
            details=details,
            exception=exc,
        )

        return jsonify(self.formatter.format(error)), classified.status_code
