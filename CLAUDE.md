# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Errium is a lightweight error normalization/translation library for APIs. It intercepts uncaught
exceptions, HTTP exceptions, and request validation errors, and standardizes them into a
consistent, frontend-safe JSON response shape. FastAPI, Flask, Django Ninja, and Django REST
Framework are all supported today; the package is split into a framework-agnostic core plus a
thin adapter per framework (see Architecture, and `ARCHITECTURE.md` for the full writeup).

## Commands

Dependency management and running things goes through `uv`.

```bash
uv sync                       # install/sync dev dependencies into .venv (includes flask, django-ninja, and drf extras)
uv run pytest                 # run the full test suite
uv run pytest --tb=short      # shorter tracebacks
uv run pytest tests/unit/test_classification.py::test_generic_exception_fallback  # single test
uv run ruff check .           # lint
uv run ruff format .          # format (CI uses `ruff format --check .`)
uv run mypy src               # type check (strict mode; mypy needs an explicit target, src is what CI checks)
```

Tests are split into `tests/unit` and `tests/integration` (the latter drives a real app end-to-end via
`fastapi.testclient.TestClient`, `flask.Flask.test_client()`, `ninja.testing.TestClient`, or DRF's
`rest_framework.test.APIRequestFactory`). `tests/conftest.py` configures a minimal Django settings
module (including `REST_FRAMEWORK["EXCEPTION_HANDLER"]`) before collection — required because
`errium_ninja`/`errium_drf` can't even be imported without Django settings configured first.
`pytest-asyncio` runs in `auto` mode, so async tests don't need an explicit marker. CI
(`.github/workflows/ci.yml`) runs ruff, ruff format --check, mypy, and pytest across Python
3.11/3.12 on every push/PR to `main`.

## Architecture

The codebase is deliberately split into five packages under `src/`:

- **`errium_core`** — framework-agnostic. Contains the classification engine, contracts (dataclasses),
  formatters, normalizers, tracing, and settings. Nothing here imports FastAPI, Starlette, or Flask
  directly where avoidable — it detects framework exception types by duck-typing instead (e.g.
  `errium_core/classifiers/validation.py` matches FastAPI's `RequestValidationError` by class name,
  `errium_core/classifiers/database.py` matches SQLAlchemy exceptions by walking the MRO for a
  `sqlalchemy.` module path), so the core stays dependency-light.
- **`errium`** — the FastAPI-specific adapter layer: the ASGI middleware, the
  `RequestValidationError` exception handler, and FastAPI/Starlette-specific classifiers.
- **`errium_flask`** — the Flask-specific adapter layer: the `ErriumFlask` extension
  (`init_app(app)` pattern) and `WerkzeugHTTPExceptionClassifier`.
- **`errium_ninja`** — the Django Ninja adapter layer: `register_errium(api)` (registered via
  Ninja's own `api.exception_handler(...)` decorator style, not a class), plus
  `NinjaValidationErrorClassifier`, `NinjaHttpErrorClassifier`, and `DjangoHttp404Classifier`.
- **`errium_drf`** — the Django REST Framework adapter layer: `errium_exception_handler(exc,
  context)` (a plain function pointed at from `REST_FRAMEWORK["EXCEPTION_HANDLER"]` in settings,
  not a decorator or class), plus `DRFValidationErrorClassifier`, `DRFAPIExceptionClassifier`,
  `DjangoHttp404Classifier`, `DjangoPermissionDeniedClassifier`, and its own
  `flatten_drf_errors` normalizer in `normalizers.py`.

When adding support for another framework (Express.js is next — see `ROADMAP.md`), follow this
same pattern: put framework-specific classifiers/handlers in a new `src/errium_<framework>`
package and reuse `errium_core` untouched.

### Request flow

1. `errium.middleware.error_middleware.ErriumMiddleware` (a Starlette `BaseHTTPMiddleware`) wraps
   `call_next` in try/except, catching anything that escapes normal request handling (generic
   exceptions and `HTTPException`s). It owns its own `ClassificationEngine` instance, registered with
   `FastAPIHTTPExceptionClassifier` and `FastAPIValidationErrorClassifier`.
2. `errium.handlers.validation_handler.validation_exception_handler` is registered separately via
   `app.add_exception_handler(RequestValidationError, ...)` because Starlette resolves
   `RequestValidationError` through FastAPI's exception-handler mechanism, not through middleware
   exception propagation. It builds its own `ClassificationEngine` too and additionally runs
   `ValidationNormalizer` to beautify the raw Pydantic error list into a flat field→message dict.
3. Both paths converge on the same contracts: a `ClassifiedError` (category/status/message) is
   produced by the classification engine, wrapped into a `StandardizedError`, then rendered to a
   dict by `DefaultFormatter` and returned as a `JSONResponse`.

The Flask adapter (`errium_flask.extension.ErriumFlask`) is simpler: a single
`app.register_error_handler(Exception, ...)` registration covers both `HTTPException`s (from
`flask.abort()`) and uncaught exceptions, since Flask dispatches both to a registered `Exception`
handler when no more specific handler exists. It also runs `ValidationNormalizer` when the caught
exception is a pydantic `ValidationError`, since Flask has no built-in request-validation exception
type of its own.

The Django Ninja adapter (`errium_ninja.extension.register_errium`) registers one shared handler
against four exception types via `api.exception_handler(...)`: `ninja.errors.ValidationError`,
`ninja.errors.HttpError`, `django.http.Http404`, and the base `Exception`. This is necessary
because it must **override** Ninja's own built-in default handlers for those same four types
(Ninja registers its own defaults on `NinjaAPI` construction) — Ninja's default `Exception`
handler re-raises when Django's `DEBUG` setting is off rather than returning JSON, which
`register_errium` replaces with a handler that always returns Errium's standardized response.
Before normalizing, it also strips a Ninja-specific quirk: for a single-Schema body/form param,
Ninja's `loc` includes a synthetic segment equal to the endpoint's *parameter name* (e.g.
`("body", "payload", "password")`) — `_flatten_ninja_errors()` drops that segment so `details`
keys match FastAPI/Flask's flat field names instead of leaking the parameter name. Neither
`django` nor `rest_framework` ship type stubs, so `pyproject.toml` has `[[tool.mypy.overrides]]`
entries silencing `import-untyped` for both rather than pulling in `django-stubs`.

The DRF adapter (`errium_drf.handler.errium_exception_handler`) is a plain function, not a class or
registration call — DRF resolves it via the `REST_FRAMEWORK["EXCEPTION_HANDLER"]` setting.
`APIView.dispatch()` wraps every view call in `except Exception: self.handle_exception(exc)`,
which calls this function; DRF's *own* default handler chooses to return `None` for anything that
isn't `APIException`/`Http404`/`PermissionDenied`, which makes `handle_exception` re-raise into
Django's plain 500 handling. `errium_exception_handler` never returns `None` — the
`ClassificationEngine`'s `GenericExceptionClassifier` fallback covers everything else — so it
achieves full catch-everything parity with the other adapters purely through the settings hook,
no extra middleware required. Validation errors keep DRF's own `400` status code (via
`exc.status_code`) rather than the `422` the other adapters use, since that's DRF's established
convention. DRF's `ValidationError.detail` has a different shape than pydantic's (a tree of
already-human-readable `ErrorDetail` strings), so `errium_drf.normalizers.flatten_drf_errors`
does its own recursive flattening rather than reusing `ValidationNormalizer`.

Note each entry point (FastAPI middleware, FastAPI validation handler, Flask extension, Ninja
`register_errium`, DRF's `errium_exception_handler`) constructs its own `ClassificationEngine`
rather than sharing one — keep that in mind when registering custom classifiers, they need to be
registered in every entry point they should apply to.

### Classification engine (`errium_core/classifiers/engine.py`)

- `ClassificationEngine` holds a priority-sorted list of classifiers (`ExceptionClassifier` protocol:
  a `priority: int` property + `classify(exc) -> ClassifiedError | None`). Higher priority runs
  first; ties default to 100.
- `ValidationExceptionClassifier` (priority 150) and `DatabaseExceptionClassifier` (priority 140)
  are always registered by the engine's `__init__` — they're the framework-agnostic classifiers
  (Pydantic/FastAPI validation errors, and SQLAlchemy errors detected without importing SQLAlchemy).
- Adapter-specific classifiers (`FastAPIHTTPExceptionClassifier`,
  `FastAPIValidationErrorClassifier`, `WerkzeugHTTPExceptionClassifier`,
  `NinjaHttpErrorClassifier`, `DjangoHttp404Classifier`, `DRFAPIExceptionClassifier`, ...) use
  higher priorities (200+) so they win over the generic classifiers when both could match.
  `FastAPIHTTPExceptionClassifier`, `WerkzeugHTTPExceptionClassifier`, `NinjaHttpErrorClassifier`,
  and `DRFAPIExceptionClassifier` all share the same status-code → category table via
  `errium_core/classifiers/status_mapping.py`'s `category_for_status_code()` — update that one
  function if the mapping needs to change, not each adapter separately. Note `DjangoHttp404Classifier`
  and `DjangoPermissionDeniedClassifier` are duplicated (not shared) between `errium_ninja` and
  `errium_drf` — each adapter package stays self-contained and only depends on `errium_core`, never
  on another adapter.
- If no classifier matches, `GenericExceptionClassifier` is used as the fallback, always producing a
  500 `INTERNAL_SERVER_ERROR`.
- A classifier's `classify()` must return `None` (not raise) when it doesn't handle a given
  exception type, so the engine can fall through to the next one.

### Error categories and response shape

`errium_core/contracts/categories.py` defines the closed set of `ErrorCategory` string values
(`VALIDATION_ERROR`, `AUTHENTICATION_ERROR`, `AUTHORIZATION_ERROR`, `RESOURCE_NOT_FOUND`,
`DUPLICATE_RESOURCE`, `DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`). The final JSON response
(`DefaultFormatter.format`) always includes `success`, `status_code`, `code`, `message`, `trace_id`,
`timestamp`, `details`. In debug mode (see below) it also includes a `debug` block with exception
class name, message, full stack trace, and contextual hints keyed off status code.

### Dev vs. prod sanitization

`errium_core/config/settings.py` holds a process-global `ErriumSettings(debug: bool)`, sourced from
the `ERRIUM_DEBUG` env var at import time. `DefaultFormatter` uses `get_settings().debug` to decide
whether to sanitize 5xx errors down to a generic `INTERNAL_SERVER_ERROR` message and whether to
attach the `debug` block. Tests mutate this at runtime via `set_settings(...)` — when writing tests
that depend on debug/prod behavior, reset settings between tests since the underlying state is a
module-level singleton.

### Validation normalization

`errium_core/normalizers/validation.py` (`ValidationNormalizer`) turns FastAPI/Pydantic's raw
`errors()` list (list of dicts with `loc`, `type`, `msg`) into a flat `{field_path: message}` dict.
It strips the leading `body`/`query`/`header`/`path`/`formData` location segment, looks up a
human-readable message template by error `type` then by `msg` (exact, then substring match), and
falls back to the raw message if nothing matches. Custom field-message mappings can be injected via
`ValidationNormalizer(custom_mappings={...})`.

## Git Workflow

### Commit size

Prefer small, logically scoped commits. As a rough guide, keep commits under ~10-15 files; if a change spans more than that (e.g. core classifier changes + a framework adapter + tests together), split it into separate commits by concern — `errium_core` first, then the adapter package(s), then tests. Avoid bulk commits that bundle unrelated classifiers, adapters, or normalizers together.

### Commit message conventions

- Start every message with a category prefix, capitalized, followed by a dash and a space:
  - `Feature - ` for new functionality
  - `Bug - ` for bug fixes
  - `Refactor - ` for internal restructuring with no behavior change
  - `Test - ` for test-only additions or fixes
  - `Chore - ` for config, deps, tooling, docs
- After the prefix, use well-capitalized, grammatically correct sentences.
- Keep messages concise — max 2 lines total. No bullet lists, no verbose explanations.
- Example: `Feature - Add DatabaseExceptionClassifier for SQLAlchemy errors`

### Push restriction

Claude may commit freely when it judges a commit boundary has been reached, following the rules above. **Claude must never push commits to the remote on its own.** Only push when explicitly told, e.g. "let's push the changes and move to new features." Committing locally is fine at any time; pushing requires explicit instruction every time.