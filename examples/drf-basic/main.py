import django
from django.conf import settings

# A minimal inline settings module so this file is runnable standalone.
# In a real project, configure Django and REST_FRAMEWORK normally and skip this.
settings.configure(
    DEBUG=True,
    DATABASES={},
    USE_TZ=True,
    ALLOWED_HOSTS=["*"],
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
    REST_FRAMEWORK={"EXCEPTION_HANDLER": "errium_drf.errium_exception_handler"},
)
django.setup()

from rest_framework import serializers  # noqa: E402
from rest_framework.decorators import api_view  # noqa: E402
from rest_framework.request import Request  # noqa: E402
from rest_framework.response import Response  # noqa: E402


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


@api_view(["POST"])
def create_user(request: Request) -> Response:
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.validated_data)


# Wire into your project's urls.py:
#   from main import create_user
#   urlpatterns = [path("users", create_user)]
