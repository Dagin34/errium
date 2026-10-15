from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from errium.engine import get_engine
from errium.middleware.error_middleware import to_json_response
from errium_core.formatters.default import DefaultFormatter
from errium_core.normalizers.http_detail import flatten_http_detail
from errium_core.pipeline import handle_error

# Headers that describe the original (replaced) body, not the new one.
_BODY_HEADERS = {"content-length", "content-type", "content-encoding"}


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Exception handler for Starlette/FastAPI `HTTPException`.

    Starlette's own `ExceptionMiddleware` turns an `HTTPException` (including the
    router's 404/405) into a response *inside* user middleware, so
    `ErriumMiddleware` never sees it. Registering this handler routes them
    through Errium instead, preserving any headers set on the exception.
    """
    headers = {
        key: value
        for key, value in (getattr(exc, "headers", None) or {}).items()
        if key.lower() not in _BODY_HEADERS
    }
    return to_json_response(
        handle_error(
            exc,
            engine=get_engine(request),
            formatter=DefaultFormatter(),
            details=lambda: flatten_http_detail(exc.detail),
            headers=headers,
        )
    )
