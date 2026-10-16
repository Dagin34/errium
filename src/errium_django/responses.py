from django.http import HttpRequest, HttpResponse, JsonResponse

from errium_core.classifiers.django_native import DjangoExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.classifiers.loader import load_classifiers
from errium_core.contracts.categories import ErrorCategory
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.pipeline import HandledError, fallback_error, handle_error
from errium_core.tracing.trace import (
    TRACE_ID_HEADER,
    resolve_trace_id,
    set_current_trace_id,
)
from errium_django.classifiers import Resolver404Classifier

_engine: ClassificationEngine | None = None
_formatter = DefaultFormatter()


def get_engine() -> ClassificationEngine:
    global _engine
    if _engine is None:
        from django.conf import settings

        config = getattr(settings, "ERRIUM", None) or {}
        _engine = ClassificationEngine(
            load_classifiers(list(config.get("CLASSIFIERS", [])))
        )
        _engine.register(Resolver404Classifier())
        _engine.register(DjangoExceptionClassifier(validation_status=422))
    return _engine


def request_trace_id(request: HttpRequest) -> str:
    """Assign the request's trace id once; exposed as `request.errium_trace_id`."""
    existing = getattr(request, "errium_trace_id", None)
    if isinstance(existing, str):
        return existing
    trace_id = resolve_trace_id(request.META.get("HTTP_X_REQUEST_ID"))
    request.errium_trace_id = trace_id
    set_current_trace_id(trace_id)
    return trace_id


def json_error_response(request: HttpRequest, exc: Exception) -> HttpResponse:
    """Render `exc` as Errium's standard JSON envelope. Never raises."""
    handled = handle_error(
        exc,
        engine=get_engine(),
        formatter=_formatter,
        trace_id=request_trace_id(request),
        method=request.method,
        path=request.path,
    )
    return _to_response(handled)


def _to_response(handled: HandledError) -> HttpResponse:
    try:
        response = JsonResponse(handled.body, status=handled.status_code)
    except Exception:
        handled = fallback_error(None, handled.trace_id)
        response = JsonResponse(handled.body, status=handled.status_code)
    for name, value in handled.headers.items():
        response[name] = value
    return response


def method_not_allowed_response(
    request: HttpRequest, allow: str | None = None
) -> HttpResponse:
    """The envelope for a bare 405 that has no exception behind it."""
    trace_id = request_trace_id(request)
    error = StandardizedError(
        status_code=405,
        code=ErrorCategory.METHOD_NOT_ALLOWED.value,
        message="Method not allowed.",
        trace_id=trace_id,
    )
    headers = {TRACE_ID_HEADER: trace_id}
    if allow:
        headers["Allow"] = allow
    return _to_response(
        HandledError(
            status_code=405,
            body=_formatter.format(error),
            trace_id=trace_id,
            headers=headers,
        )
    )
