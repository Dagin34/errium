from errium_core.contracts.categories import ErrorCategory

_STATUS_CODE_CATEGORIES: dict[int, ErrorCategory] = {
    400: ErrorCategory.BAD_REQUEST,
    401: ErrorCategory.AUTHENTICATION,
    403: ErrorCategory.AUTHORIZATION,
    404: ErrorCategory.NOT_FOUND,
    405: ErrorCategory.METHOD_NOT_ALLOWED,
    406: ErrorCategory.NOT_ACCEPTABLE,
    408: ErrorCategory.TIMEOUT,
    409: ErrorCategory.CONFLICT,
    410: ErrorCategory.GONE,
    413: ErrorCategory.PAYLOAD_TOO_LARGE,
    415: ErrorCategory.UNSUPPORTED_MEDIA_TYPE,
    422: ErrorCategory.VALIDATION,
    429: ErrorCategory.RATE_LIMITED,
    502: ErrorCategory.SERVICE_UNAVAILABLE,
    503: ErrorCategory.SERVICE_UNAVAILABLE,
    504: ErrorCategory.TIMEOUT,
}

# Generic, exception-free messages for the 5xx categories whose code survives
# production sanitization (everything else collapses to INTERNAL_SERVER_ERROR).
SAFE_5XX_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.SERVICE_UNAVAILABLE: "The service is temporarily unavailable.",
    ErrorCategory.TIMEOUT: "The request timed out.",
}


def category_for_status_code(status_code: int) -> ErrorCategory:
    """Map a raw HTTP status code to a standard Errium error category.

    Shared by every HTTP-framework adapter (FastAPI, Flask, ...) so status
    code -> category mapping is defined once, in the framework-agnostic core.
    Any other 4xx maps to BAD_REQUEST; any other status to INTERNAL_SERVER_ERROR.
    """
    category = _STATUS_CODE_CATEGORIES.get(status_code)
    if category is not None:
        return category
    if 400 <= status_code < 500:
        return ErrorCategory.BAD_REQUEST
    return ErrorCategory.INTERNAL
