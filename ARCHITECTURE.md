# Architecture

This document describes how Errium is put together internally. It's aimed at contributors and at
anyone building a new framework adapter.

## Design goal: core vs. adapters

Errium is split into a framework-agnostic core and thin, framework-specific adapters:

```
src/
├── errium_core/     # framework-agnostic: classification, contracts, formatting, settings
├── errium/          # FastAPI / Starlette adapter
├── errium_flask/    # Flask adapter
└── errium_ninja/    # Django Ninja adapter
```

`errium_core` never imports FastAPI, Starlette, or Flask. Where it needs to recognize a
framework's exception type without depending on that framework (e.g. FastAPI's
`RequestValidationError`), it does so by duck-typing — checking `exc.__class__.__name__` or
walking `type(exc).__mro__` for a known module path — rather than importing the framework. See
`errium_core/classifiers/validation.py` and `errium_core/classifiers/database.py` for examples.

Each adapter package (`errium`, `errium_flask`, `errium_ninja`) contributes:
- One or more `ExceptionClassifier` implementations for framework-specific exception types
  (`FastAPIHTTPExceptionClassifier`, `WerkzeugHTTPExceptionClassifier`, ...).
- An integration point that hooks into the framework's error-handling mechanism (a middleware for
  FastAPI/Starlette, an extension class for Flask) and wires everything together: build a
  `ClassificationEngine`, classify the exception, wrap it in a `StandardizedError`, format it with
  `DefaultFormatter`, and return the framework's native JSON response type.

Adding support for a new framework means adding a new `src/errium_<framework>` package that
follows this same pattern and reuses `errium_core` untouched.

## Core building blocks (`errium_core`)

### Contracts (`errium_core/contracts/`)

- `ErrorCategory` (`categories.py`) — the closed set of category strings every response's `code`
  field can take: `VALIDATION_ERROR`, `AUTHENTICATION_ERROR`, `AUTHORIZATION_ERROR`,
  `RESOURCE_NOT_FOUND`, `DUPLICATE_RESOURCE`, `DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`.
- `ClassifiedError` (`classified_error.py`) — the minimal output of classification: `category`,
  `status_code`, `message`.
- `StandardizedError` (`error.py`) — the full internal representation of an error before
  formatting: adds `trace_id`, `success`, `timestamp`, optional `details`, and the original
  `exception` (kept around so the formatter can build debug info from it).

### Classification (`errium_core/classifiers/`)

- `ExceptionClassifier` (`base.py`) — a `Protocol` every classifier implements: a `priority: int`
  property and `classify(exc) -> ClassifiedError | None`. Returning `None` means "not my
  exception type, try the next classifier."
- `ClassificationEngine` (`engine.py`) — holds classifiers sorted by priority (highest first,
  ties default to 100). `classify(exc)` runs each classifier in order and returns the first
  non-`None` result, falling back to `GenericExceptionClassifier` (always `INTERNAL_SERVER_ERROR`,
  500) if nothing matches. On construction it always registers `ValidationExceptionClassifier`
  (priority 150) and `DatabaseExceptionClassifier` (priority 140) — the two classifiers that are
  genuinely framework-agnostic. Adapters register their own higher-priority, framework-specific
  classifiers (priority 200+) on top of that.
- `ValidationExceptionClassifier` (`validation.py`) — matches Pydantic `ValidationError` or
  anything named `RequestValidationError`, always mapping to `VALIDATION_ERROR` / 422.
- `DatabaseExceptionClassifier` (`database.py`) — matches SQLAlchemy exceptions by walking the
  exception class's MRO for a `sqlalchemy.` module path (no SQLAlchemy dependency). An
  `IntegrityError` whose message looks like a uniqueness violation (`unique constraint`,
  `duplicate key`, `duplicate entry`, `already exists`) maps to `DUPLICATE_RESOURCE` / 409;
  any other SQLAlchemy error maps to `DATABASE_ERROR` / 500.
- `GenericExceptionClassifier` (`generic.py`) — the engine's fallback, not part of the
  priority-sorted list.
- `status_mapping.py` — `category_for_status_code(status_code)`, the shared HTTP-status-code →
  `ErrorCategory` table (401→AUTHENTICATION, 403→AUTHORIZATION, 404→NOT_FOUND, 409→DUPLICATE,
  422→VALIDATION, else→INTERNAL). `FastAPIHTTPExceptionClassifier`,
  `WerkzeugHTTPExceptionClassifier`, and `NinjaHttpErrorClassifier` all use this so the mapping is
  defined once.

Each adapter entry point (the FastAPI middleware, the FastAPI validation handler, the Flask
extension, the Ninja registration function) constructs its **own** `ClassificationEngine`
instance rather than sharing one. A custom classifier meant to apply everywhere needs to be
registered on each entry point.

### Formatting (`errium_core/formatters/`)

- `ErrorFormatter` (`base.py`) — a `Protocol`: `format(error: StandardizedError) -> dict[str, Any]`.
- `DefaultFormatter` (`default.py`) — the only implementation. Produces the response body:
  `success`, `status_code`, `code`, `message`, `trace_id`, `timestamp`, `details`. Reads
  `get_settings().debug`:
  - In production (`debug=False`), any `status_code >= 500` has its `code`/`message` sanitized to
    a generic `INTERNAL_SERVER_ERROR` / "An unexpected error occurred." regardless of what the
    classifier produced, so internals never leak to clients.
  - In debug mode (`debug=True`), a `debug` block is added with the exception class name, its
    message, a full formatted stack trace, and a short list of contextual hints keyed off the
    status code (e.g. "Check the 'details' field..." for 422).

### Normalization (`errium_core/normalizers/validation.py`)

`ValidationNormalizer.normalize(errors)` turns a raw Pydantic/FastAPI `errors()` list (dicts with
`loc`, `type`, `msg`) into a flat `{field_path: message}` dict:
1. Strips a leading `body`/`query`/`header`/`path`/`formData` location segment.
2. Looks up a human-readable message template by error `type`, then by `msg` (exact match, then
   substring match against known markers), falling back to the raw message if nothing matches.
3. Formats `{field_name}` placeholders (e.g. `password` → "Password") and normalizes punctuation
   (capitalized start, trailing period).

Custom field-message mappings can be injected via `ValidationNormalizer(custom_mappings={...})`.
The FastAPI validation handler, the Flask extension, and the Django Ninja adapter all use this to
turn a raw pydantic `ValidationError`/`RequestValidationError`/Ninja `ValidationError` into the
beautified `details` dict.

### Settings (`errium_core/config/settings.py`)

`ErriumSettings(debug: bool)` is a process-global singleton, sourced from the `ERRIUM_DEBUG`
env var at import time (`"true"`/`"1"`/`"yes"`, case-insensitive). `get_settings()` /
`set_settings()` read and replace it. Tests mutate this directly via `set_settings(...)`; because
it's a module-level singleton, tests that rely on a specific debug/production mode should set it
explicitly rather than assuming a default.

### Tracing (`errium_core/tracing/trace.py`)

`generate_trace_id()` returns a fresh `uuid4()` string per error, used to correlate the
client-facing response with server-side logs.

## Adapter: FastAPI (`errium`)

Two independent entry points exist because Starlette resolves `RequestValidationError`
differently from other exceptions:

1. **`ErriumMiddleware`** (`middleware/error_middleware.py`) — a Starlette `BaseHTTPMiddleware`
   that wraps `call_next` in try/except, catching anything that escapes normal request handling
   (uncaught exceptions and `HTTPException`s). Registers `FastAPIHTTPExceptionClassifier`
   (priority 200) and `FastAPIValidationErrorClassifier` (priority 210).
2. **`validation_exception_handler`** (`handlers/validation_handler.py`) — registered separately
   via `app.add_exception_handler(RequestValidationError, ...)`, because FastAPI resolves
   `RequestValidationError` through its own exception-handler mechanism rather than letting it
   propagate through middleware. It builds its own `ClassificationEngine`, classifies the error,
   and additionally runs `ValidationNormalizer` on `exc.errors()` to produce beautified `details`.

`errium/classifiers.py` holds `FastAPIHTTPExceptionClassifier` (matches
`fastapi.HTTPException` / `starlette.exceptions.HTTPException`, maps status code via
`category_for_status_code`) and `FastAPIValidationErrorClassifier` (matches
`RequestValidationError` specifically, at higher priority than the core's generic validation
classifier).

Both entry points converge on the same contract: build a `ClassifiedError`, wrap it in a
`StandardizedError`, format with `DefaultFormatter`, return as a `fastapi.responses.JSONResponse`.

## Adapter: Flask (`errium_flask`)

- **`WerkzeugHTTPExceptionClassifier`** (`classifiers.py`) — matches `werkzeug.exceptions.HTTPException`
  (what `flask.abort()` raises), maps its `.code` via `category_for_status_code`, uses
  `.description` as the message.
- **`ErriumFlask`** (`extension.py`) — a Flask extension following the standard
  `init_app(app)` pattern (works with `ErriumFlask(app)` directly or the app-factory pattern via
  `ErriumFlask().init_app(app)`). It registers a single catch-all handler via
  `app.register_error_handler(Exception, ...)`. Flask dispatches both `HTTPException`s (e.g. from
  `abort()`) and unhandled generic exceptions to a registered `Exception` handler when no more
  specific handler exists, so one registration is sufficient — unlike the FastAPI adapter, Flask
  doesn't need a second, separately-registered handler for validation errors.
- The handler classifies the exception, and if it's a pydantic `ValidationError` (there's no
  Flask-native request-validation exception type — this covers the common case of validating a
  request body with a Pydantic model by hand inside a view), runs it through
  `ValidationNormalizer` for the same beautified `details` the FastAPI adapter produces.
- Response is returned as `(jsonify(...), status_code)`, Flask's standard
  `(body, status_code)` response tuple form.

## Adapter: Django Ninja (`errium_ninja`)

Django Ninja is the closest architectural match to FastAPI: it's Pydantic-native, and its request
validation errors carry the same `loc`/`type`/`msg` shape FastAPI's do. The adapter follows the
same registration style Ninja itself uses — decorators on a `NinjaAPI` instance — rather than a
Flask-style extension class:

- **`register_errium(api: NinjaAPI)`** (`extension.py`) — the sole entry point. It builds a
  `ClassificationEngine`, registers `NinjaValidationErrorClassifier`, `NinjaHttpErrorClassifier`,
  and `DjangoHttp404Classifier`, then registers one shared handler function against
  `ninja.errors.ValidationError`, `ninja.errors.HttpError`, `django.http.Http404`, and the base
  `Exception` via `api.exception_handler(...)`. This **overrides Ninja's own built-in default
  handlers** for those same exception types (Ninja registers defaults for all four when a
  `NinjaAPI` is constructed) — notably, Ninja's default `Exception` handler re-raises when
  `django.conf.settings.DEBUG` is `False` ("let django deal with it"), which would bypass
  Errium's JSON contract entirely in production. `register_errium` always returns a standardized
  response instead, deferring the debug/production decision to Errium's own `ERRIUM_DEBUG`
  setting rather than Django's `DEBUG`.
- **`classifiers.py`**:
  - `NinjaValidationErrorClassifier` (priority 210) — matches `ninja.errors.ValidationError`.
  - `NinjaHttpErrorClassifier` (priority 200) — matches `ninja.errors.HttpError`, which also
    covers its subclasses `AuthenticationError`, `AuthorizationError`, and `Throttled` via
    `isinstance`. Maps `exc.status_code` through `category_for_status_code`.
  - `DjangoHttp404Classifier` (priority 200) — matches Django's own `Http404` (e.g. from
    `get_object_or_404`), which isn't an `HttpError` subclass and needs its own classifier.
- **Ninja's `loc` quirk**: when a single Pydantic `Schema` is used as a body/form parameter (the
  idiomatic pattern — `def view(request, payload: SomeSchema)`), Ninja wraps validation errors
  behind a synthetic segment equal to the *endpoint's parameter name* (e.g.
  `("body", "payload", "password")`), instead of FastAPI's flat `("body", "password")`. Query,
  path, and header params don't get this wrapper — Ninja already flattens those. Left alone, this
  would leak the arbitrary parameter name into the `details` dict's keys and break contract parity
  with the other adapters. `extension.py`'s `_flatten_ninja_errors()` strips that one synthetic
  segment (for `body`/`form` locations only) before handing errors to `ValidationNormalizer`, so
  `details` keys always match what FastAPI/Flask would produce for the same field.

Because `NinjaAPI`/`django.http` can't even be imported without Django settings configured first,
anything that touches `errium_ninja` — including its own test suite — needs
`django.conf.settings.configure(...)` + `django.setup()` called before import. See `tests/conftest.py`.

## Response contract

Every adapter produces the same JSON shape:

```json
{
  "success": false,
  "status_code": 422,
  "code": "VALIDATION_ERROR",
  "message": "Validation failed.",
  "trace_id": "87b003a8-7c15-4a6c-9c76-a05b22b109e2",
  "timestamp": "2026-05-27T12:00:00Z",
  "details": {
    "password": "Password is required."
  }
}
```

With `ERRIUM_DEBUG=true`, a `debug` object is added (exception class name, message, full stack
trace, contextual hints). See `DefaultFormatter` above for the sanitization rule that keeps this
out of production responses.

## Testing layout

- `tests/unit/` — pure unit tests against classifiers, the normalizer, and the formatter, with no
  running app.
- `tests/integration/` — drives a real app (`fastapi.testclient.TestClient` /
  `flask.Flask.test_client()` / `ninja.testing.TestClient`) end-to-end through the adapter's
  actual wiring, asserting on the full JSON response shape.
- `tests/conftest.py` — configures a minimal Django settings module and calls `django.setup()`
  before test collection, so `errium_ninja` (and anything else that needs Django) is importable.
  No-op for the FastAPI/Flask suites.
