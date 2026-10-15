from typing import Any

NON_FIELD_KEY = "_"


def is_django_validation_error(exc: BaseException) -> bool:
    return any(
        klass.__name__ == "ValidationError"
        and klass.__module__.startswith("django.core.exceptions")
        for klass in type(exc).__mro__
    )


def flatten_django_validation_error(exc: Any) -> dict[str, str]:
    """Flatten `django.core.exceptions.ValidationError` into {field: message}.

    Field errors keep their field name (messages joined with "; "); errors not
    tied to a field (a bare message or Django's `__all__`) use the "_" key.
    """
    if hasattr(exc, "error_dict"):
        flat: dict[str, str] = {}
        for field, messages in exc.message_dict.items():
            key = NON_FIELD_KEY if field == "__all__" else str(field)
            flat[key] = "; ".join(str(message) for message in messages)
        return flat
    return {NON_FIELD_KEY: "; ".join(str(message) for message in exc.messages)}
