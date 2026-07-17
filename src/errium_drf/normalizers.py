from typing import Any

NON_FIELD_ERRORS_KEY = "non_field_errors"


def flatten_drf_errors(detail: Any, prefix: str = "") -> dict[str, str]:
    """Flatten DRF's ValidationError.detail tree into a flat {field: message} dict.

    DRF's detail is a recursive structure: dicts (field -> nested errors) and
    lists (multiple ErrorDetail messages for one field, or one dict per item
    for a many=True serializer), with already human-readable ErrorDetail
    leaves. Unlike ValidationNormalizer, this needs no type/msg template
    mapping - DRF's messages are ready to use as-is.
    """
    flattened: dict[str, str] = {}

    if isinstance(detail, dict):
        for key, value in detail.items():
            field_key = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_drf_errors(value, field_key))
        return flattened

    if isinstance(detail, list):
        messages = [str(item) for item in detail if not isinstance(item, dict | list)]
        nested = [item for item in detail if isinstance(item, dict | list)]

        if messages:
            flattened[prefix or NON_FIELD_ERRORS_KEY] = " ".join(messages)

        for index, item in enumerate(nested):
            item_key = f"{prefix}[{index}]" if prefix else str(index)
            flattened.update(flatten_drf_errors(item, item_key))

        return flattened

    flattened[prefix or NON_FIELD_ERRORS_KEY] = str(detail)
    return flattened
