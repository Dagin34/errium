import django
from django.conf import settings

# A minimal inline settings module so this file is runnable standalone.
# In a real project, configure Django normally and skip this block.
settings.configure(DEBUG=True, DATABASES={}, USE_TZ=True, ALLOWED_HOSTS=["*"])
django.setup()

from ninja import NinjaAPI, Schema  # noqa: E402

from errium_ninja import register_errium  # noqa: E402

api = NinjaAPI()

register_errium(api)


class UserCreate(Schema):
    email: str
    password: str


@api.post("/users")
def create_user(request, payload: UserCreate):
    return payload.dict()


# Wire into your project's urls.py:
#   from main import api
#   urlpatterns = [path("api/", api.urls)]
