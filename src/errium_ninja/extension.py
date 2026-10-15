from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja.errors import ValidationError as NinjaValidationError

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.pipeline import fallback_error, handle_error
from errium_core.tracing.trace import resolve_trace_id, set_current_trace_id
from errium_ninja.classifiers import (
    DjangoHttp404Classifier,
    NinjaHttpErrorClassifier,
    NinjaValidationErrorClassifier,
)

# Locations where Ninja wraps a single Schema-typed parameter behind a
# synthetic field named after the endpoint's own parameter (e.g. `payload`),
# giving loc like ("body", "payload", "password") instead of a flat
# ("body", "password"). Query/path/header params don't get this wrapper -
# Ninja already flattens those back to the real field name.
_WRAPPED_LOCATIONS = ("body", "form")


def _flatten_ninja_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip Ninja's synthetic parameter-name wrapper so `details` keys match
    the flat field names FastAPI and Flask produce for the same validation
    failure."""
    flattened = []
    for error in errors:
        loc = list(error.get("loc", []))
        if len(loc) >= 3 and loc[0] in _WRAPPED_LOCATIONS:
            loc = [loc[0], *loc[2:]]
        flattened.append({**error, "loc": loc})
    return flattened


def _request_trace_id(request: HttpRequest) -> str:
    """Assign the request's trace id once; exposed as `request.errium_trace_id`."""
    existing = getattr(request, "errium_trace_id", None)
    if isinstance(existing, str):
        return existing
    trace_id = resolve_trace_id(request.META.get("HTTP_X_REQUEST_ID"))
    request.errium_trace_id = trace_id
    set_current_trace_id(trace_id)
    return trace_id


def register_errium(api: NinjaAPI) -> None:
    """Register Errium's exception handlers on a NinjaAPI instance.

    Overrides Ninja's built-in default handlers for ValidationError, HttpError,
    Http404, and generic Exception so every error response uses Errium's
    standardized contract instead of Ninja's `{"detail": ...}` shape. Notably,
    Ninja's default `Exception` handler re-raises in production (letting Django
    render its own error page) — this replaces that with a handler that always
    returns a standardized JSON response, deferring to Errium's own
    `ERRIUM_DEBUG` setting for sanitization.
    """
    engine = ClassificationEngine()
    engine.register(NinjaValidationErrorClassifier())
    engine.register(NinjaHttpErrorClassifier())
    engine.register(DjangoHttp404Classifier())

    formatter = DefaultFormatter()
    normalizer = ValidationNormalizer()

    def _handle_exception(request: HttpRequest, exc: Exception) -> HttpResponse:
        # Beautify Ninja's raw validation errors into a flat field->message dict,
        # mirroring the FastAPI and Flask adapters.
        details = None
        if isinstance(exc, NinjaValidationError):
            ninja_exc = exc

            def details() -> dict[str, str]:
                return normalizer.normalize(_flatten_ninja_errors(ninja_exc.errors))

        handled = handle_error(
            exc,
            engine=engine,
            formatter=formatter,
            details=details,
            trace_id=_request_trace_id(request),
            method=request.method,
            path=request.path,
        )
        try:
            response = api.create_response(
                request, handled.body, status=handled.status_code
            )
        except Exception:
            handled = fallback_error(None, handled.trace_id)
            response = api.create_response(request, handled.body, status=500)
        for name, value in handled.headers.items():
            response[name] = value
        return response

    api.exception_handler(Exception)(_handle_exception)
    api.exception_handler(Http404)(_handle_exception)
    api.exception_handler(HttpError)(_handle_exception)
    api.exception_handler(NinjaValidationError)(_handle_exception)
