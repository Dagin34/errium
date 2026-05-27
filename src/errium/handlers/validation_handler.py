from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errium.classifiers import FastAPIValidationErrorClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.tracing.trace import generate_trace_id


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Exception handler for FastAPI validation errors."""
    classification_engine = ClassificationEngine()
    # Register validation classifier specifically
    classification_engine.register(FastAPIValidationErrorClassifier())
    classified = classification_engine.classify(exc)

    # Beautify the raw error details
    normalizer = ValidationNormalizer()
    normalized_details = normalizer.normalize(exc.errors())

    error = StandardizedError(
        status_code=classified.status_code,
        code=classified.category,
        message=classified.message,
        trace_id=generate_trace_id(),
        success=False,
        details=normalized_details,
        exception=exc,
    )

    formatter = DefaultFormatter()

    return JSONResponse(
        status_code=classified.status_code,
        content=formatter.format(error),
    )
