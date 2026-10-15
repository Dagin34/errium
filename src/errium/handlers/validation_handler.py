from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errium.classifiers import FastAPIValidationErrorClassifier
from errium.middleware.error_middleware import to_json_response
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.pipeline import handle_error


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Exception handler for FastAPI validation errors."""
    classification_engine = ClassificationEngine()
    # Register validation classifier specifically
    classification_engine.register(FastAPIValidationErrorClassifier())

    normalizer = ValidationNormalizer()

    return to_json_response(
        handle_error(
            exc,
            engine=classification_engine,
            formatter=DefaultFormatter(),
            # Beautify the raw error details
            details=lambda: normalizer.normalize(exc.errors()),
        )
    )
