from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.tracing.trace import generate_trace_id


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    classification_engine = ClassificationEngine()
    classified = classification_engine.classify(exc)

    error = StandardizedError(
        status_code=classified.status_code,
        code=classified.category,
        message=classified.message,
        trace_id=generate_trace_id(),
    )

    formatter = DefaultFormatter()

    return JSONResponse(
        status_code=classified.status_code,
        content=formatter.format(error),
    )
