import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={},
        USE_TZ=True,
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        REST_FRAMEWORK={"EXCEPTION_HANDLER": "errium_drf.errium_exception_handler"},
    )
    django.setup()
