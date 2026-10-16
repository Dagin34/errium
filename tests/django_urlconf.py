"""URLconf + middleware used by the errium_django integration tests."""

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, JsonResponse
from django.urls import path
from ninja import NinjaAPI

from errium_ninja import register_errium

api = NinjaAPI(urls_namespace="errium_test_api")
register_errium(api)


@api.get("/ping")
def ping(request):  # type: ignore[no-untyped-def]
    return {"ok": True}


def item(request, pk: int):  # type: ignore[no-untyped-def]
    return JsonResponse({"pk": pk})


def plain_ok(request):  # type: ignore[no-untyped-def]
    return HttpResponse("fine")


def plain_boom(request):  # type: ignore[no-untyped-def]
    raise ValueError("view exploded")


def plain_forbidden(request):  # type: ignore[no-untyped-def]
    raise PermissionDenied("no entry")


def plain_suspicious(request):  # type: ignore[no-untyped-def]
    raise SuspiciousOperation("weird")


class BoomMiddleware:
    """Raises for any request carrying the `X-Boom` header."""

    def __init__(self, get_response):  # type: ignore[no-untyped-def]
        self.get_response = get_response

    def __call__(self, request):  # type: ignore[no-untyped-def]
        if "X-Boom" in request.headers:
            raise RuntimeError("middleware exploded")
        return self.get_response(request)


urlpatterns = [
    path("api/", api.urls),
    path("item/<int:pk>/", item),
    path("plain/ok/", plain_ok),
    path("plain/boom/", plain_boom),
    path("plain/forbidden/", plain_forbidden),
    path("plain/suspicious/", plain_suspicious),
]

handler400 = "errium_django.handler400"
handler403 = "errium_django.handler403"
handler404 = "errium_django.handler404"
handler500 = "errium_django.handler500"
