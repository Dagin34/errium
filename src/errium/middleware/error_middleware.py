from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from errium.engine import build_engine, request_trace_id
from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.formatters.default import DefaultFormatter
from errium_core.pipeline import HandledError, fallback_error, handle_error


def to_json_response(handled: HandledError) -> JSONResponse:
    """Wrap a handled error in a JSONResponse, falling back if it can't render."""
    try:
        return JSONResponse(
            status_code=handled.status_code,
            content=handled.body,
            headers=handled.headers,
        )
    except Exception:
        generic = fallback_error(None, handled.trace_id)
        return JSONResponse(status_code=generic.status_code, content=generic.body)


class ErriumMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        classifiers: list[ExceptionClassifier] | None = None,
        engine: ClassificationEngine | None = None,
    ) -> None:
        """Create the middleware.

        `classifiers` are added to the default FastAPI engine; `engine` replaces
        it entirely (you then own registering the FastAPI classifiers).
        """
        super().__init__(app)

        self.classification_engine = engine or build_engine(classifiers)

        self.formatter = DefaultFormatter()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        trace_id = request_trace_id(request)
        # Let the HTTPException / validation handlers share this middleware's
        # engine, so a custom classifier applies everywhere in the app.
        if getattr(request.app.state, "errium_engine", None) is None:
            request.app.state.errium_engine = self.classification_engine
        try:
            return await call_next(request)

        except Exception as exc:
            return to_json_response(
                handle_error(
                    exc,
                    engine=self.classification_engine,
                    formatter=self.formatter,
                    trace_id=trace_id,
                    method=request.method,
                    path=request.url.path,
                )
            )
