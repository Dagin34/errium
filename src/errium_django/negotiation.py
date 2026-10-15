from django.conf import settings
from django.http import HttpRequest

DEFAULT_JSON_PATH_PREFIXES = ["/api/"]


def json_path_prefixes() -> list[str]:
    """`settings.ERRIUM_JSON_PATH_PREFIXES`, default `["/api/"]`."""
    prefixes = getattr(settings, "ERRIUM_JSON_PATH_PREFIXES", None)
    if prefixes is None:
        return list(DEFAULT_JSON_PATH_PREFIXES)
    return [str(prefix) for prefix in prefixes]


def _media_ranges(accept: str) -> list[tuple[str, float]]:
    ranges = []
    for part in accept.split(","):
        media_type, _, params = part.strip().partition(";")
        quality = 1.0
        for param in params.split(";"):
            name, _, value = param.strip().partition("=")
            if name.strip() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if media_type.strip():
            ranges.append((media_type.strip().lower(), quality))
    return ranges


def prefers_json(accept: str) -> bool:
    """True if the `Accept` header ranks a JSON type above HTML.

    Wildcards are ignored (browsers and curl both send `*/*`), so only an
    explicit JSON media type counts. On a tie the earlier-listed type wins.
    """
    best: tuple[float, int, bool] | None = None
    for index, (media_type, quality) in enumerate(_media_ranges(accept)):
        is_json = media_type == "application/json" or media_type.endswith("+json")
        is_html = media_type in ("text/html", "application/xhtml+xml")
        if quality <= 0 or not (is_json or is_html):
            continue
        candidate = (quality, -index, is_json)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return bool(best and best[2])


def wants_json(request: HttpRequest) -> bool:
    """Should this request get an Errium JSON error rather than Django's page?

    True when the client prefers JSON via `Accept`, or the path starts with one
    of `ERRIUM_JSON_PATH_PREFIXES` (default `["/api/"]`).
    """
    if prefers_json(request.headers.get("Accept", "")):
        return True
    path = request.path_info or request.path
    return any(path.startswith(prefix) for prefix in json_path_prefixes())
