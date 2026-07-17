import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={},
        USE_TZ=True,
        ALLOWED_HOSTS=["*"],
    )
    django.setup()
