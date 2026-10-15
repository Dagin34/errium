"""Django URLconf error handlers returning Errium's JSON envelope.

Wire them in the root URLconf::

    handler400 = "errium_django.handler400"
    handler403 = "errium_django.handler403"
    handler404 = "errium_django.handler404"
    handler500 = "errium_django.handler500"

A request gets the JSON envelope only if it prefers JSON (`Accept`) or its path
starts with one of `settings.ERRIUM_JSON_PATH_PREFIXES` (default `["/api/"]`);
everyone else still gets Django's own error page.
"""

import sys

from django.http import Http404, HttpRequest, HttpResponse
from django.views import defaults

from errium_django.negotiation import wants_json
from errium_django.responses import json_error_response


def handler404(
    request: HttpRequest, exception: Exception | None = None
) -> HttpResponse:
    if not wants_json(request):
        return defaults.page_not_found(request, exception or Http404())
    return json_error_response(request, exception or Http404())


def handler403(
    request: HttpRequest, exception: Exception | None = None
) -> HttpResponse:
    from django.core.exceptions import PermissionDenied

    if not wants_json(request):
        return defaults.permission_denied(request, exception or PermissionDenied())
    return json_error_response(request, exception or PermissionDenied())


def handler400(
    request: HttpRequest, exception: Exception | None = None
) -> HttpResponse:
    from django.core.exceptions import SuspiciousOperation

    if not wants_json(request):
        return defaults.bad_request(request, exception or SuspiciousOperation())
    return json_error_response(request, exception or SuspiciousOperation())


def handler500(request: HttpRequest) -> HttpResponse:
    """Django calls this inside its `except` block, so the exception is available."""
    if not wants_json(request):
        return defaults.server_error(request)
    exc = sys.exc_info()[1]
    if not isinstance(exc, Exception):
        exc = RuntimeError("Server error")
    return json_error_response(request, exc)
