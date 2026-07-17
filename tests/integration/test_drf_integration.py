from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from errium_core.config.settings import ErriumSettings, set_settings

factory = APIRequestFactory()


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


@api_view(["POST"])
def create_user(request: Request) -> Response:
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.validated_data)


@api_view(["GET"])
def missing(request: Request) -> Response:
    raise NotFound("User not found")


@api_view(["GET"])
def trigger_error(request: Request) -> Response:
    raise RuntimeError("Something went wrong internally")


def test_drf_validation_error_beautified():
    request = factory.post("/users", {"email": "not-an-email"}, format="json")
    response = create_user(request)
    response.render()
    data = response.data

    assert response.status_code == 400
    assert data["success"] is False
    assert data["status_code"] == 400
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed."
    assert "trace_id" in data
    assert "timestamp" in data
    assert data["details"]["email"] == "Enter a valid email address."
    assert data["details"]["password"] == "This field is required."


def test_drf_api_exception_is_standardized():
    request = factory.get("/missing")
    response = missing(request)
    response.render()
    data = response.data

    assert response.status_code == 404
    assert data["success"] is False
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert data["message"] == "User not found"


def test_drf_uncaught_exception_is_standardized_not_reraised():
    """DRF's own default EXCEPTION_HANDLER returns None for non-APIException
    types, which makes APIView.handle_exception re-raise. errium_exception_handler
    must never do that - this is the whole point of the adapter."""
    set_settings(ErriumSettings(debug=False))

    request = factory.get("/trigger-500")
    response = trigger_error(request)
    response.render()
    data = response.data

    assert response.status_code == 500
    assert data["success"] is False
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected error occurred."
    assert "debug" not in data


def test_drf_internal_error_debug():
    set_settings(ErriumSettings(debug=True))

    request = factory.get("/trigger-500")
    response = trigger_error(request)
    response.render()
    data = response.data

    assert "debug" in data
    debug_info = data["debug"]
    assert debug_info["exception"] == "RuntimeError"
    assert debug_info["message"] == "Something went wrong internally"
    assert "RuntimeError: Something went wrong internally" in debug_info["stack_trace"]
