from typing import Any

from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.tracing.trace import generate_trace_id
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

_formatter = DefaultFormatter()


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
    trace_id = generate_trace_id()
    classified = _engine.classify(exc)

    # Beautify DRF's raw ValidationError.detail tree into a flat
    # field->message dict, mirroring the other adapters' `details` field.
    details = None
    if isinstance(exc, DRFValidationError):
        details = flatten_drf_errors(exc.detail)

    error = StandardizedError(
        status_code=classified.status_code,
        code=classified.category,
        message=classified.message,
        trace_id=trace_id,
        success=False,
        details=details,
        exception=exc,
    )

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

    return Response(
        _formatter.format(error), status=classified.status_code, headers=headers
    )
