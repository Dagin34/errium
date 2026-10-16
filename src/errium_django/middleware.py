import sys
from collections.abc import Callable
from typing import Any

from django.core.signals import got_request_exception
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

from errium_django.negotiation import wants_json
from errium_django.responses import (
    json_error_response,
    method_not_allowed_response,
    request_trace_id,
)

_EXC_ATTR = "_errium_exception"


def _remember_exception(sender: Any, request: Any = None, **kwargs: Any) -> None:
    """Record the exception Django is about to turn into a bare 500 page."""
    exc = sys.exc_info()[1]
    if request is not None and exc is not None:
        setattr(request, _EXC_ATTR, exc)


class ErriumDjangoMiddleware:
    """Normalise errors Django would otherwise render as HTML.

    Put it **first** in `MIDDLEWARE`. For clients that want JSON (see
    `errium_django.negotiation.wants_json`) it:

    - assigns the request's trace id (`request.errium_trace_id`) up front;
    - turns exceptions raised by plain Django views (`process_exception`) and by
      *later* middleware into the Errium envelope - Django converts the latter
      into a 500 page before this middleware sees them, so it records the
      exception through the `got_request_exception` signal and swaps the page;
    - turns bare `HttpResponseNotAllowed` (405) responses, e.g. Django Ninja's
      own method check, into the envelope while keeping the `Allow` header.

    Exceptions in middleware listed *before* this one are only caught if the
    URLconf sets `handler500 = "errium_django.handler500"`.
    """

    sync_capable = True
    async_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        got_request_exception.connect(
            _remember_exception, dispatch_uid="errium_django_remember_exception"
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_trace_id(request)
        response = self.get_response(request)

        if not wants_json(request):
            return response

        if isinstance(response, HttpResponseNotAllowed):
            return method_not_allowed_response(
                request, response.get("Allow") if response.has_header("Allow") else None
            )

        exc = getattr(request, _EXC_ATTR, None)
        if (
            exc is not None
            and response.status_code >= 500
            and "json" not in response.get("Content-Type", "")
        ):
            return json_error_response(request, exc)
        return response

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        if wants_json(request):
            return json_error_response(request, exception)
        return None
