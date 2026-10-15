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
