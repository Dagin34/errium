# Errium – Intelligent API Error Normalization for FastAPI

Errium is a lightweight, framework-agnostic error normalization and translation middleware for modern APIs. It intercepts uncaught exceptions, HTTP exceptions, and request validation errors, standardizing them into clean, consistent, and frontend-safe JSON responses.

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

Install Errium in your virtual environment:

```bash
uv pip install errium
# Or using traditional pip
pip install errium
```

---

## 🛠️ Usage Example

Integrating Errium into your FastAPI codebase takes less than two lines:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from errium import ErriumMiddleware
from errium.handlers.validation_handler import validation_exception_handler

app = FastAPI()

# 1. Add Middleware to catch raw & HTTP exceptions
app.add_middleware(ErriumMiddleware)

# 2. Add validation exception handler to capture validation errors
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Your endpoints go here...
```

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

See `ROADMAP.md` for more detail on what's done and what's planned.
