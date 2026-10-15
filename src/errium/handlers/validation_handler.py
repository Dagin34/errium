from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errium.engine import get_engine
from errium.middleware.error_middleware import to_json_response
from errium_core.classifiers.validation import is_malformed_body
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.validation import ValidationNormalizer
from errium_core.pipeline import handle_error


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Exception handler for FastAPI validation errors."""
    normalizer = ValidationNormalizer()

    return to_json_response(
        handle_error(
            exc,
            engine=get_engine(request),
            formatter=DefaultFormatter(),
            # Beautify the raw error details
            details=lambda: (
                None if is_malformed_body(exc) else normalizer.normalize(exc.errors())
            ),
        )
    )
