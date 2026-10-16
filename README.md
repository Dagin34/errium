# Errium – Intelligent API Error Normalization for FastAPI

[![PyPI version](https://img.shields.io/pypi/v/errium.svg)](https://pypi.org/project/errium/)
[![Python versions](https://img.shields.io/pypi/pyversions/errium.svg)](https://pypi.org/project/errium/)
[![License: MIT](https://img.shields.io/pypi/l/errium.svg)](https://github.com/Dagin34/errium/blob/main/LICENSE)
[![CI](https://github.com/Dagin34/errium/actions/workflows/ci.yml/badge.svg)](https://github.com/Dagin34/errium/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-errium.dagmawi.et-1a1a1a)](https://errium.dagmawi.et/)

Errium is a lightweight, framework-agnostic error normalization and translation middleware for modern APIs. It intercepts uncaught exceptions, HTTP exceptions, and request validation errors, standardizing them into clean, consistent, and frontend-safe JSON responses.

📖 **[Read the documentation → errium.dagmawi.et](https://errium.dagmawi.et/)** — installation, per-framework guides, core concepts, and architecture.

---

## ⚡ The Problem

Building APIs with modern frameworks (like FastAPI) often yields inconsistent error responses, causing friction for frontend teams:

- **Ugly FastAPI Validation Errors**: Deeply nested, verbose, and difficult to parse direct Pydantic formats.
- **Inconsistent Backend Responses**: Uncaught internal exceptions return unhandled stack trace leaks or plain text errors depending on where they occurred.
- **Frontend Integration Pain**: Frontend engineers are forced to write custom parsers for every microservice, parsing varying response layouts.

## 🚀 The Solution

Errium provides a unified error classification, normalization, and formatting pipeline:
1. **Intelligent Middleware (`ErriumMiddleware`)**: Transparently intercepts all request lifecycles.
2. **Classification Engine (`ClassificationEngine`)**: Dynamically resolves error categories, status codes, and user-facing messages.
3. **Beautification & Normalization**: Transforms nested, complex errors into flat, friendly key-value details.
4. **Environment-Aware Sanitization**: Exposes detailed backtrace logs in `development` and secures system internals in `production`.

---

## 🌟 Features

- 🟢 **Unified Error Format**: Every single API error response uses the exact same structured JSON contract.
- 💅 **Validation Beautifier**: Automatically maps common validation types (e.g. `missing`, invalid emails, nulls) into clean, capitalized localized messages.
- 🆔 **Trace IDs**: Seamlessly correlates client-facing responses with server-side application logs.
- 🛡️ **Dev vs. Prod Mode**: Exposes traceback objects, raw exception names, and actionable debug hints in development, while sanitizing server details in production.
- 🔌 **Extensible Plugin Classifier**: Register custom classifiers with sorting priority evaluation.

---

## 📦 Installation

Errium is published on [PyPI](https://pypi.org/project/errium/) and requires Python 3.11+.

```bash
uv pip install errium
# Or using traditional pip
pip install errium
```

The base install ships the core plus the FastAPI adapter. Each other framework is an extra:

```bash
uv pip install "errium[flask]"   # Flask
uv pip install "errium[ninja]"   # Django Ninja
uv pip install "errium[drf]"     # Django REST Framework
uv pip install "errium[django]"  # errium_django helpers only (error pages outside Ninja/DRF)
```

> **Note:** the base install requires `fastapi`/`starlette`, so the Flask, Ninja and DRF extras
> install them too. Their adapters never import FastAPI at runtime; it is install footprint only.

> **Note:** Errium depends on `fastapi`, not `fastapi[standard]`, so it stays light for Flask and
> Django users. If you were relying on Errium to pull in a server, install one yourself
> (`uv pip install uvicorn`).

All five packages ship a `py.typed` marker, so type checkers see Errium's annotations directly.

---

## 🛠️ Usage Example

Integrating Errium into your FastAPI codebase takes one line:

```python
from fastapi import FastAPI
import errium

app = FastAPI()

# Adds the middleware (uncaught exceptions) and registers handlers for
# HTTPException (including routing 404/405) and request validation errors.
errium.install(app)

# Your endpoints go here...
```

`errium.install(app)` is equivalent to the manual wiring below, which still works but also needs
the `HTTPException` handler to normalise `HTTPException`s (Starlette resolves those *inside*
user middleware, so the middleware alone never sees them):

```python
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from errium import ErriumMiddleware
from errium.handlers.http_handler import http_exception_handler
from errium.handlers.validation_handler import validation_exception_handler

app.add_middleware(ErriumMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
```

**Mounted sub-apps** (`app.mount("/v1", v1_app)`) do not inherit the parent's middleware or
handlers: call `errium.install(v1_app)` on each mounted app.

A structured `HTTPException(detail={...})` / `detail=[...]` keeps `message` as the HTTP phrase
(e.g. "Bad Request") and exposes the value in `details` (dict entries as `{key: str(value)}`, list
items as `{"0": ..., "1": ...}`). Headers set on the exception (`Retry-After`, `WWW-Authenticate`,
`X-*`) are preserved.

Flask is supported too, via the `errium[flask]` extra:

```bash
uv pip install "errium[flask]"
```

```python
from flask import Flask
from errium_flask import ErriumFlask

app = Flask(__name__)

# Registers a single catch-all error handler covering HTTP exceptions,
# uncaught exceptions, and pydantic validation errors.
ErriumFlask(app)

# Your routes go here...
```

Django Ninja is supported too, via the `errium[ninja]` extra:

```bash
uv pip install "errium[ninja]"
```

```python
from ninja import NinjaAPI
from errium_ninja import register_errium

api = NinjaAPI()

# Registers handlers covering Ninja's ValidationError, HttpError (and its
# AuthenticationError/AuthorizationError/Throttled subclasses), Django's
# Http404, and generic exceptions.
register_errium(api)

# Your endpoints go here...
```

Django REST Framework is supported too, via the `errium[drf]` extra:

```bash
uv pip install "errium[drf]"
```

```python
# settings.py
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "errium_drf.errium_exception_handler",
}
```

That's it — every exception raised inside a DRF view (`APIException` family, Django's `Http404`/
`PermissionDenied`, and any other uncaught exception) now returns Errium's standardized response.
Note: validation errors keep DRF's own `400` status code rather than the `422` the other adapters
use, matching DRF's established convention.

### Configuration

| Variable | Effect |
|---|---|
| `ERRIUM_DEBUG` | `true`/`1`/`yes`/`on` (case-insensitive, whitespace ignored) adds a `debug` block and stops sanitizing 5xx messages. Anything else stays off. The mode is logged once at import (INFO on the `errium` logger), with a WARNING if debug is on while `ERRIUM_ENV`/`APP_ENV`/`ENVIRONMENT`/`ENV` says production. |
| `ERRIUM_TRUST_REQUEST_ID` | Reuse a valid inbound `X-Request-ID` as the `trace_id`. |

`errium.__version__` (and `errium_core`, `errium_flask`, `errium_ninja`, `errium_drf`,
`errium_django`) report the installed version.

### FastAPI middleware order (CORS)

Starlette runs middleware in reverse order of registration: the one added **last** is outermost.
Add `CORSMiddleware` **after** Errium so it wraps it; otherwise an uncaught-exception 500 is
produced *outside* CORS and the browser reports a CORS failure instead of showing the JSON body.

```python
errium.install(app)                    # adds ErriumMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example.com"])  # after
```

### Known limitations

- **Mid-stream failures cannot be normalized.** If a `StreamingResponse` /
  `StreamingHttpResponse` generator raises after the first chunk, the status line and headers
  are already sent; the connection just ends. A generator failing *before* its first byte on
  FastAPI still returns the 200 it started with. Validate and fetch what you can before
  returning a streaming response.
- Mounted FastAPI sub-apps need their own `errium.install(sub_app)`.
- For Django, errors raised before Django middleware runs (or when `DEBUG = True`) may still
  render Django's own page; see "Django project setup" above.

### Custom classifiers

Map your own exception types to a status, category and message. The one-liner works on every
adapter at once (it is a process-wide registry consulted by all engines):

```python
import errium

class OutOfStock(Exception): ...

errium.register(OutOfStock, status=409, message="That item is out of stock.")

# or, as a class decorator (category defaults to the standard one for the status):
@errium.register(status=429, category="RATE_LIMITED")
class SlowDown(Exception): ...
```

For full control, write a classifier (`priority` property + `classify(exc) -> ClassifiedError | None`)
and pass it to the adapter. Higher priority runs first; built-in adapter classifiers are 200+,
`register(...)` uses 300.

| Adapter | How to pass classifiers |
|---|---|
| FastAPI | `errium.install(app, classifiers=[...])`, or `app.add_middleware(ErriumMiddleware, classifiers=[...])` |
| Flask | `ErriumFlask(app, classifiers=[...])` |
| Django Ninja | `register_errium(api, classifiers=[...])` |
| DRF | `REST_FRAMEWORK["EXCEPTION_HANDLER"] = "errium_drf.errium_exception_handler"` plus `ERRIUM = {"CLASSIFIERS": ["myapp.errors.QuotaClassifier"]}`, or `make_exception_handler(classifiers=[...])` |
| errium_django | `ERRIUM = {"CLASSIFIERS": [...]}` in Django settings |

Every adapter also takes `engine=` to replace the default `ClassificationEngine` outright
(`build_engine(...)` in each adapter package builds the default one). On FastAPI, one engine is
shared by the middleware and both exception handlers.

### Trace IDs and logging

Every error response carries a `trace_id` (also sent as an `X-Trace-Id` response header), and
Errium logs each handled exception on the `"errium"` logger — `ERROR` with the traceback for 5xx,
a one-line `WARNING` for 4xx — with that same `trace_id` in the message, so a client-reported id
can be matched to a log line. Errium never configures logging handlers; attach your own:

```python
import logging
logging.getLogger("errium").addHandler(logging.StreamHandler())
```

To use the id in your own code: `request.state.errium_trace_id` (FastAPI), `flask.g.errium_trace_id`
(Flask), `request.errium_trace_id` (Django Ninja / DRF), or `errium_core.tracing.current_trace_id()`
anywhere in the request's context. Set `ERRIUM_TRUST_REQUEST_ID=true` to reuse a valid inbound
`X-Request-ID` (≤128 characters of letters, digits and `._:-`) as the `trace_id`; by default a
fresh uuid4 is generated.

### Django project setup: errors outside the view layer

Ninja's and DRF's handlers only see exceptions raised *inside* their views. An unknown URL, a URL
converter mismatch (`/item/abc/` for `<int:pk>`), Ninja's own 405, and an exception in a Django
middleware are rendered by Django itself as HTML. Cover them with the `errium_django` helpers
(`pip install "errium[django]"`, or the `ninja`/`drf` extras):

```python
# urls.py (root URLconf)
handler400 = "errium_django.handler400"
handler403 = "errium_django.handler403"
handler404 = "errium_django.handler404"
handler500 = "errium_django.handler500"

# settings.py
MIDDLEWARE = [
    "errium_django.ErriumDjangoMiddleware",  # first, so it wraps everything below
    # ...
]
ERRIUM_JSON_PATH_PREFIXES = ["/api/"]  # optional; this is the default
```

A request gets the JSON envelope only if it prefers JSON (`Accept: application/json`) or its path
starts with one of `ERRIUM_JSON_PATH_PREFIXES`; browsers and other HTML clients still get Django's
normal error pages. `ErriumDjangoMiddleware` also converts exceptions raised by *later* middleware
and plain Django views, and turns a bare 405 (Ninja's method check) into the envelope while keeping
its `Allow` header. Exceptions in middleware listed *before* it are only covered by
`handler500`. Django's technical 500 page replaces `handler500` while `DEBUG = True`.

---

## 🔍 Before vs. After

### ❌ Before Errium (Ugly FastAPI Validation)
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "password"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

###  After Errium (Cleaned, Beautified Response)
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

---

## 🗺️ Roadmap

Errium is designed framework-agnostically at the core. We are planning the following integrations:

- [x] Flask Adapter Layer
- [x] Django Ninja Adapter Layer
- [x] Django REST Framework Adapter Layer
- [ ] Express.js Adapter Layer (JavaScript port)
- [ ] AI-Powered Developer Suggestions & Self-Healing Hints

See [the roadmap](https://errium.dagmawi.et/roadmap) (or `ROADMAP.md`) for more detail on what's
done and what's planned.
