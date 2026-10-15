# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- FastAPI: `HTTPException`, unknown-route 404, 405 and body-parse 400 responses are now Errium
  envelopes instead of raw `{"detail": ...}`, and `HTTPException(500, "secret")` no longer leaks
  its message in production. Register `errium.handlers.http_handler.http_exception_handler` for
  `HTTPException` (or just call `errium.install(app)`).

- The error path can no longer raise. Exceptions whose `__str__`/`__repr__` fails, or whose
  arguments are unprintable, now produce the standard JSON envelope on every adapter (previously
  FastAPI/Django/Flask fell back to their own non-JSON 500 pages). A last-resort handler returns a
  generic `INTERNAL_SERVER_ERROR` envelope with a fresh `trace_id` if classification or formatting
  itself fails.

### Changed

- Response sizes are bounded. `details` is capped at 50 entries (keys 200 chars, messages 500);
  when entries are dropped a `"_truncated": "N more"` key is added (absent otherwise).
  `debug.message` is capped at 2,000 characters and `debug.stack_trace` at 20,000 (the tail is
  kept).
- Debug output for validation errors no longer echoes the request: `debug.message` and
  `debug.stack_trace` list only `loc`, `msg` and `type`, never the submitted `input`/`ctx` (a
  1 MB body used to come back as a 2 MB response and could contain passwords).
- DRF `details`: errors not tied to a field use the key `_` instead of `non_field_errors`
  (also `address._` for nested serializers), and several messages for one field are joined with
  `"; "` instead of a space. Per-framework message wording is unchanged. **Breaking for clients
  that read `details.non_field_errors`.**
- Ninja: a bare pydantic `ValidationError` raised from a view - typically Ninja validating the
  endpoint's return value against its `response=` schema - is now `500 INTERNAL_SERVER_ERROR`
  instead of `422 VALIDATION_ERROR`, since it is a server bug the client cannot fix. Request
  validation (`ninja.errors.ValidationError`) is unchanged.
- **Visible contract change (recommend 0.2.0).** `code` is now consistent with `status_code` for
  HTTP errors: 400 `BAD_REQUEST`, 405 `METHOD_NOT_ALLOWED`, 406 `NOT_ACCEPTABLE`, 408/504
  `TIMEOUT`, 409 `CONFLICT`, 410 `GONE`, 413 `PAYLOAD_TOO_LARGE`, 415 `UNSUPPORTED_MEDIA_TYPE`,
  429 `RATE_LIMITED`, 502/503 `SERVICE_UNAVAILABLE`; any other 4xx is `BAD_REQUEST`. Previously
  all of these were `INTERNAL_SERVER_ERROR`. Clients switching on `code` should handle the new
  values; the field set and the existing seven values are unchanged. A database uniqueness
  violation is still `DUPLICATE_RESOURCE`; a plain HTTP 409 is now `CONFLICT`.
- In production, 502/503/504 keep their `SERVICE_UNAVAILABLE`/`TIMEOUT` code (with a generic
  message) instead of collapsing to `INTERNAL_SERVER_ERROR`; every other 5xx still does, and no
  5xx response carries `details` in production.
- A request body that is not parseable JSON is now `400 BAD_REQUEST` ("Malformed request body.")
  on every adapter (FastAPI used to answer `422 VALIDATION_ERROR`).

### Added

- Public classifier registration on every adapter. `errium.register(MyError, status=409,
  message=...)` (also usable as a class decorator) registers process-wide for all adapters via the
  new `errium_core.registry`. `ErriumMiddleware(app, classifiers=..., engine=...)`,
  `errium.install(app, classifiers=..., engine=...)`, `ErriumFlask(app, classifiers=...,
  engine=...)`, `register_errium(api, classifiers=..., engine=...)`, DRF's
  `make_exception_handler(...)` and `settings.ERRIUM["CLASSIFIERS"]`, and a `build_engine()` per
  adapter. The FastAPI middleware and handlers now share one engine. Old call forms keep working.
- New `errium_django` package for errors outside the Ninja/DRF view layer: `handler400`,
  `handler403`, `handler404`, `handler500` URLconf handlers and `ErriumDjangoMiddleware`. Unknown
  URLs, URL-converter mismatches, Ninja's own 405, and exceptions in Django middleware now return
  the Errium envelope for clients that prefer JSON (or paths under `ERRIUM_JSON_PATH_PREFIXES`,
  default `["/api/"]`); HTML clients keep Django's pages. New `django` extra.
- Django-native exceptions are classified on Ninja and DRF instead of collapsing to 500:
  `PermissionDenied` -> 403, `SuspiciousOperation` -> 400 `BAD_REQUEST`,
  `RequestDataTooBig`/`TooManyFieldsSent`/`TooManyFilesSent` -> 413 `PAYLOAD_TOO_LARGE`,
  `django.core.exceptions.ValidationError` -> 422 (Ninja) / 400 (DRF) with a flat `details`
  dict, `ObjectDoesNotExist` -> 404. New `errium_core.classifiers.django_native.DjangoExceptionClassifier`
  (duck-typed, no Django import in the core).
- `DatabaseExceptionClassifier` now recognises `django.db`, `sqlite3`, `psycopg`, `psycopg2`,
  `asyncpg`, `pymysql` and `MySQLdb` exceptions (by module path, no hard imports) in addition to
  SQLAlchemy: unique violations -> 409 `DUPLICATE_RESOURCE`, other errors -> `DATABASE_ERROR`.
- Protocol headers on exceptions are preserved on the error response across adapters: `Allow`,
  `Retry-After`, `WWW-Authenticate`, `Location` and `Content-Range`, read from
  `exc.get_headers()`, `exc.headers` and `exc.response.headers`. Fixes Flask dropping
  `Retry-After` (429) and `Allow` (405). Other headers are not copied.
- Every handled exception is now logged on the `errium` logger (`ERROR` + traceback for >= 500,
  one-line `WARNING` for 4xx) with `trace_id`, status, category, method and path, so the
  `trace_id` a client reports can be matched to a log line. Errium still configures no handlers.
- The trace id is exposed to application code: `request.state.errium_trace_id` (FastAPI),
  `flask.g.errium_trace_id`, `request.errium_trace_id` (Django), and
  `errium_core.tracing.current_trace_id()`. Error responses carry an `X-Trace-Id` header.
- `ERRIUM_TRUST_REQUEST_ID=true` reuses a valid inbound `X-Request-ID` as the `trace_id`
  (default off; the id stays a fresh uuid4).
- `errium.install(app, *, debug=None)`: one-call FastAPI setup (middleware + `HTTPException` and
  `RequestValidationError` handlers, one shared engine on `app.state`). Idempotent and safe on
  mounted sub-apps; call it for each mounted app. The old two-line setup keeps working.
- `errium.handlers.http_handler.http_exception_handler`, preserving exception headers.
- `errium_core.safe.safe_str(exc, limit=2000)`: renders an exception as text without ever raising
  (`str` -> `repr` -> class name) and truncates the result. `debug.message` now uses it.
- `errium_core.pipeline.handle_error`: the single classify -> format path shared by all adapters.

## [0.1.2] — 2026-09-15

Documentation-only release. No code changes — published so the new documentation site is linked
from the PyPI project page, which snapshots project metadata and the README per version.

### Changed

- Documentation moved to https://errium.dagmawi.et/. The `Homepage` and `Documentation` project
  URLs now point there instead of at the previous MkDocs site on GitHub Pages, and the README
  links to it.
- The MkDocs site at https://dagin34.github.io/errium/ is retired; it now serves only a notice
  pointing to the new domain.

## [0.1.1] — 2026-09-03

Documentation-only release. No code changes — published so the updated README renders on the
PyPI project page, which snapshots it per version.

### Changed

- README now carries PyPI, Python version, license, and CI badges, documents the `flask`/`ninja`/
  `drf` extras together, notes the shipped `py.typed` markers, and flags that a server
  (`uvicorn`) must be installed separately since Errium depends on `fastapi`, not
  `fastapi[standard]`.

### Added

- This changelog, published to the docs site at https://dagin34.github.io/errium/changelog/.

## [0.1.0] — 2026-09-03

First public release, [published on PyPI](https://pypi.org/project/errium/).

### Added

- **Core pipeline** (`errium_core`) — framework-agnostic `ClassificationEngine`, the
  `ExceptionClassifier` protocol, `ClassifiedError`/`StandardizedError` contracts,
  `DefaultFormatter`, and `ValidationNormalizer`. Detects framework and SQLAlchemy exception
  types by duck-typing rather than importing them, so the core stays dependency-light.
- **FastAPI adapter** (`errium`) — `ErriumMiddleware` for uncaught and HTTP exceptions, plus
  `validation_exception_handler` for `RequestValidationError` with beautified `details`.
- **Flask adapter** (`errium_flask`) — the `ErriumFlask` extension, covering Werkzeug HTTP
  exceptions, uncaught exceptions, and pydantic validation errors raised inside views.
- **Django Ninja adapter** (`errium_ninja`) — `register_errium(api)`, overriding Ninja's built-in
  handlers for `ValidationError`, `HttpError`, `Http404`, and `Exception`.
- **Django REST Framework adapter** (`errium_drf`) — `errium_exception_handler`, wired through
  `REST_FRAMEWORK["EXCEPTION_HANDLER"]`, with its own `flatten_drf_errors` normalizer.
- **Database classification** — `DatabaseExceptionClassifier` maps SQLAlchemy errors to
  `DATABASE_ERROR`, and uniqueness violations to `DUPLICATE_RESOURCE`, with no hard SQLAlchemy
  dependency.
- **Dev vs. prod sanitization** — `ERRIUM_DEBUG` controls whether 5xx responses are sanitized and
  whether a `debug` block with the stack trace and hints is attached.
- **Typing** — all five packages ship a `py.typed` marker; the source is checked under
  `mypy --strict`.

[Unreleased]: https://github.com/Dagin34/errium/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Dagin34/errium/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Dagin34/errium/releases/tag/v0.1.0
