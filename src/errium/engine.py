from starlette.requests import Request

from errium.classifiers import (
    FastAPIHTTPExceptionClassifier,
    FastAPIValidationErrorClassifier,
)
from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine


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
