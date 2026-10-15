from dataclasses import replace

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from errium.engine import build_engine
from errium.handlers.http_handler import http_exception_handler
from errium.handlers.validation_handler import validation_exception_handler
from errium.middleware.error_middleware import ErriumMiddleware
from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.engine import ClassificationEngine
from errium_core.config.settings import get_settings, set_settings


def install(
    app: FastAPI,
    *,
    debug: bool | None = None,
    classifiers: list[ExceptionClassifier] | None = None,
    engine: ClassificationEngine | None = None,
) -> None:
    """Wire Errium into a FastAPI app in one call.

    Adds `ErriumMiddleware` (uncaught exceptions) and registers handlers for
    `HTTPException` (incl. routing 404/405) and `RequestValidationError`, all
    sharing one classification engine stored on `app.state`.

    Safe to call on a mounted sub-app - mounted apps do not inherit the parent's
    middleware or handlers, so call `install(sub_app)` for each one. Calling it
    twice on the same app is a no-op.

    `debug` overrides `ERRIUM_DEBUG` for the whole process (settings are global);
    leave it `None` to keep the environment-driven value.

    `classifiers` are added to the default engine; `engine` replaces it. Both
    apply to the middleware and both handlers.
    """
    if getattr(app.state, "errium_installed", False):
        return

    if debug is not None:
        set_settings(replace(get_settings(), debug=debug))

    shared_engine = engine or build_engine(classifiers)
    app.state.errium_engine = shared_engine
    app.state.errium_installed = True

    app.add_middleware(ErriumMiddleware, engine=shared_engine)
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # type: ignore[arg-type]
    )
