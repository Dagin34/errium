from flask import Flask, g, jsonify, request
from flask.typing import ResponseReturnValue
from pydantic import ValidationError as PydanticValidationError

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.pipeline import fallback_error, handle_error
from errium_core.tracing.trace import (
    REQUEST_ID_HEADER,
    resolve_trace_id,
    set_current_trace_id,
)
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
        app.before_request(self._assign_trace_id)
        app.register_error_handler(Exception, self._handle_exception)

    @staticmethod
    def _assign_trace_id() -> None:
        """Expose the trace id as `flask.g.errium_trace_id` before the view runs."""
        trace_id = resolve_trace_id(request.headers.get(REQUEST_ID_HEADER))
        g.errium_trace_id = trace_id
        set_current_trace_id(trace_id)

    def _handle_exception(self, exc: Exception) -> ResponseReturnValue:
        # Beautify raw pydantic validation errors into a flat field->message dict,
        # mirroring the FastAPI adapter's RequestValidationError handling.
        details = None
        if isinstance(exc, PydanticValidationError):
            pydantic_exc = exc

            def details() -> dict[str, str]:
                return self.normalizer.normalize(pydantic_exc.errors())

        handled = handle_error(
            exc,
            engine=self.classification_engine,
            formatter=self.formatter,
            details=details,
            trace_id=g.get("errium_trace_id"),
            method=request.method,
            path=request.path,
        )
        try:
            return jsonify(handled.body), handled.status_code, handled.headers
        except Exception:
            generic = fallback_error(None, handled.trace_id)
            return jsonify(generic.body), generic.status_code, generic.headers
