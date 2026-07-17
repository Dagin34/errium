# Roadmap

Errium's core (`errium_core`) is framework-agnostic by design; the work ahead is mostly about
adding thin adapters on top of it (see `ARCHITECTURE.md` for how an adapter is structured) and
rounding out the classification coverage in the core itself.

## Done

- **Core classification pipeline** — `ClassificationEngine`, the `ExceptionClassifier` protocol,
  `StandardizedError`/`ClassifiedError` contracts, `DefaultFormatter`, `ValidationNormalizer`,
  dev/prod sanitization via `ERRIUM_DEBUG`.
- **FastAPI adapter** (`errium`) — `ErriumMiddleware` for uncaught exceptions and HTTP
  exceptions, `validation_exception_handler` with beautified validation `details`.
- **Flask adapter** (`errium_flask`) — `ErriumFlask` extension covering Werkzeug HTTP exceptions,
  generic exceptions, and beautified pydantic validation errors raised manually inside views.
- **Django Ninja adapter** (`errium_ninja`) — `register_errium(api)` covering Ninja's
  `ValidationError`/`HttpError` (and its `AuthenticationError`/`AuthorizationError`/`Throttled`
  subclasses), Django's `Http404`, and generic exceptions, overriding Ninja's built-in defaults
  (which otherwise re-raise uncaught exceptions in production instead of returning JSON). Also
  strips Ninja's synthetic parameter-name wrapper from validation error locations so `details`
  keys match the other adapters.
- **Database error classification** — `DatabaseExceptionClassifier` maps SQLAlchemy errors to
  `DATABASE_ERROR`, and integrity errors that look like uniqueness violations to
  `DUPLICATE_RESOURCE`, without a hard SQLAlchemy dependency.
- **CI** — GitHub Actions workflow running `ruff check`, `ruff format --check`, `mypy`, and
  `pytest` across Python 3.11/3.12 on every push and PR to `main`.

## Planned

- **Django REST Framework adapter** — hooks in via a `REST_FRAMEWORK["EXCEPTION_HANDLER"]`
  setting function. Needs its own detail-flattening normalizer (DRF's `ErrorDetail` tree has a
  different shape than pydantic's `loc`/`type`/`msg`) rather than reusing `ValidationNormalizer`
  directly. Note: DRF's exception handler is only invoked for `APIException`/`Http404`/
  `PermissionDenied` raised inside a DRF view — a raw uncaught exception falls through to
  Django's normal 500 handling instead, so full catch-everything parity with the other adapters
  would additionally need a plain-Django `process_exception` middleware as a safety net.
- **Express.js adapter (JavaScript port)** — a separate package outside the Python distribution;
  would need its own port of the core contracts, not just an adapter.
- **AI-powered developer suggestions & self-healing hints** — extending
  `DefaultFormatter._get_debug_hints` (currently a static, status-code-keyed lookup) with
  more context-aware, possibly model-generated suggestions in debug mode.

## Notes for contributors

When picking up a new framework adapter, follow the pattern documented in `ARCHITECTURE.md`
("Design goal: core vs. adapters"): a new `src/errium_<framework>` package containing
framework-specific `ExceptionClassifier`s plus one integration point that builds a
`ClassificationEngine`, classifies, formats, and returns the framework's native response type.
Nothing in `errium_core` should need to change to support a new framework.
