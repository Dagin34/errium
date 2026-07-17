from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from errium.classifiers import (
    FastAPIHTTPExceptionClassifier,
    FastAPIValidationErrorClassifier,
)
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.tracing.trace import generate_trace_id


class ErriumMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

        self.classification_engine = ClassificationEngine()
        # Register FastAPI classifiers for high-priority handling
        self.classification_engine.register(FastAPIHTTPExceptionClassifier())
        self.classification_engine.register(FastAPIValidationErrorClassifier())

        self.formatter = DefaultFormatter()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)

        except Exception as exc:
            trace_id = generate_trace_id()

            classified = self.classification_engine.classify(exc)

            error = StandardizedError(
                status_code=classified.status_code,
                code=classified.category,
                message=classified.message,
                trace_id=trace_id,
                success=False,
                exception=exc,
            )

            return JSONResponse(
                status_code=classified.status_code,
                content=self.formatter.format(error),
            )
