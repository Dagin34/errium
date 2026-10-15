from typing import Any


def flatten_http_detail(detail: Any) -> dict[str, str] | None:
    """Turn a structured HTTP exception `detail` into a flat `details` dict.

    FastAPI/Starlette allow `HTTPException(detail=...)` to be any JSON value.
    A string is used as the response `message` and needs no `details`; a dict
    becomes `{key: str(value)}`; a list becomes `{"0": str(item), ...}`. Values
    are stringified so the response stays JSON-safe.
    """
    if isinstance(detail, dict):
        return {str(key): str(value) for key, value in detail.items()}
    if isinstance(detail, list | tuple):
        return {str(index): str(item) for index, item in enumerate(detail)}
    return None
