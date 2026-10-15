from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from errium.engine import build_engine
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
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

        # Pre-loaded with the FastAPI classifiers for high-priority handling
        self.classification_engine = build_engine()

        self.formatter = DefaultFormatter()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)

        except Exception as exc:
            return to_json_response(
                handle_error(
                    exc,
                    engine=self.classification_engine,
                    formatter=self.formatter,
                )
            )
