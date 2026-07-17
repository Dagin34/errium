from errium_core.contracts.categories import ErrorCategory

_STATUS_CODE_CATEGORIES: dict[int, ErrorCategory] = {
    401: ErrorCategory.AUTHENTICATION,
    403: ErrorCategory.AUTHORIZATION,
    404: ErrorCategory.NOT_FOUND,
    409: ErrorCategory.DUPLICATE,
    422: ErrorCategory.VALIDATION,
}


def category_for_status_code(status_code: int) -> ErrorCategory:
    """Map a raw HTTP status code to a standard Errium error category.

    Shared by every HTTP-framework adapter (FastAPI, Flask, ...) so status
    code -> category mapping is defined once, in the framework-agnostic core.
    """
    return _STATUS_CODE_CATEGORIES.get(status_code, ErrorCategory.INTERNAL)
