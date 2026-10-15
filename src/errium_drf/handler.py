from typing import Any

from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from errium_core.classifiers.django_native import DjangoExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.formatters.default import DefaultFormatter
from errium_core.pipeline import fallback_error, handle_error
from errium_core.tracing.trace import resolve_trace_id, set_current_trace_id
from errium_drf.classifiers import (
    DjangoHttp404Classifier,
    DjangoPermissionDeniedClassifier,
    DRFAPIExceptionClassifier,
    DRFValidationErrorClassifier,
)
from errium_drf.normalizers import flatten_drf_errors

_engine = ClassificationEngine()
_engine.register(DRFValidationErrorClassifier())
_engine.register(DRFAPIExceptionClassifier())
_engine.register(DjangoHttp404Classifier())
_engine.register(DjangoPermissionDeniedClassifier())
_engine.register(DjangoExceptionClassifier(validation_status=400))

_formatter = DefaultFormatter()


def _request_trace_id(request: Any) -> str | None:
    """Assign the request's trace id once; exposed as `request.errium_trace_id`."""
    if request is None:
        return None
    existing = getattr(request, "errium_trace_id", None)
    if isinstance(existing, str):
        return existing
    trace_id = resolve_trace_id(request.META.get("HTTP_X_REQUEST_ID"))
    # `request` is DRF's wrapper; set it on the underlying HttpRequest too so
    # plain Django code (middleware, templates) sees the same attribute.
    for target in (request, getattr(request, "_request", request)):
        target.errium_trace_id = trace_id
    set_current_trace_id(trace_id)
    return trace_id


def errium_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """DRF EXCEPTION_HANDLER entry point.

    Point REST_FRAMEWORK["EXCEPTION_HANDLER"] at this function's dotted path
    (or import and assign it directly). Unlike DRF's default exception_handler,
    this never returns None: `APIView.dispatch()` wraps every view call in a
    broad `except Exception`, routing it to `handle_exception()` ->
    `exception_handler(exc, context)`. DRF's own default handler chooses to
    return None for anything that isn't APIException/Http404/PermissionDenied,
    which makes `handle_exception` re-raise into Django's plain-text 500
    handling. Because this handler always returns a Response, every exception
    raised inside a DRF view gets Errium's standardized JSON contract instead.
    """
    request = context.get("request") if isinstance(context, dict) else None

    # Beautify DRF's raw ValidationError.detail tree into a flat
    # field->message dict, mirroring the other adapters' `details` field.
    details = None
    if isinstance(exc, DRFValidationError):
        drf_exc = exc

        def details() -> dict[str, str]:
            return flatten_drf_errors(drf_exc.detail)

    # Mirror DRF's default handler's header handling for auth challenges and
    # throttling, since APIView.handle_exception sets these attributes on the
    # exception before calling us.
    headers: dict[str, str] = {}
    auth_header = getattr(exc, "auth_header", None)
    if auth_header:
        headers["WWW-Authenticate"] = auth_header
    wait = getattr(exc, "wait", None)
    if wait:
        headers["Retry-After"] = str(int(wait))

    handled = handle_error(
        exc,
        engine=_engine,
        formatter=_formatter,
        details=details,
        headers=headers,
        trace_id=_request_trace_id(request),
        method=getattr(request, "method", None),
        path=getattr(request, "path", None),
    )
    try:
        return Response(
            handled.body, status=handled.status_code, headers=handled.headers
        )
    except Exception:
        generic = fallback_error(None, handled.trace_id)
        return Response(
            generic.body, status=generic.status_code, headers=generic.headers
        )
