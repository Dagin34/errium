from starlette.requests import Request

from errium.classifiers import (
    FastAPIHTTPExceptionClassifier,
    FastAPIValidationErrorClassifier,
)
from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.tracing.trace import (
    REQUEST_ID_HEADER,
    resolve_trace_id,
    set_current_trace_id,
)


def build_engine(
    classifiers: list[ExceptionClassifier] | None = None,
) -> ClassificationEngine:
    """Build a ClassificationEngine pre-loaded with the FastAPI classifiers."""
    engine = ClassificationEngine(classifiers)
    engine.register(FastAPIHTTPExceptionClassifier())
    engine.register(FastAPIValidationErrorClassifier())
    return engine


_default_engine: ClassificationEngine | None = None


def get_engine(request: Request | None = None) -> ClassificationEngine:
    """Return the engine installed on the request's app, else a shared default."""
    global _default_engine
    if request is not None:
        engine = getattr(request.app.state, "errium_engine", None)
        if isinstance(engine, ClassificationEngine):
            return engine
    if _default_engine is None:
        _default_engine = build_engine()
    return _default_engine


def request_trace_id(request: Request) -> str:
    """The trace id for this request, assigned once and exposed to app code.

    Stored on `request.state.errium_trace_id` and the `current_trace_id()`
    contextvar so handlers and application code can log it.
    """
    existing = getattr(request.state, "errium_trace_id", None)
    if isinstance(existing, str):
        return existing
    trace_id = resolve_trace_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.errium_trace_id = trace_id
    set_current_trace_id(trace_id)
    return trace_id
