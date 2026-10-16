"""Process-wide custom classifier registry: the 99 % path for custom errors.

Anything registered here applies to **every** engine (FastAPI, Flask, Ninja,
DRF, errium_django) at classification time, so one registration covers all
entry points. Per-adapter alternatives are the `classifiers=`/`engine=`
arguments each adapter accepts.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from errium_core.classifiers.base import ExceptionClassifier
from errium_core.classifiers.status_mapping import category_for_status_code
from errium_core.contracts.classified_error import ClassifiedError
from errium_core.safe import safe_str

T = TypeVar("T")

CUSTOM_PRIORITY = 300  # above every built-in classifier

_registered: list[ExceptionClassifier] = []
_version = 0


class ExceptionTypeClassifier:
    """Maps an exception type (and its subclasses) to a fixed status/category."""

    def __init__(
        self,
        exc_type: type[BaseException] | tuple[type[BaseException], ...],
        *,
        status: int,
        category: str | None = None,
        message: str | Callable[[Exception], str] | None = None,
        priority: int = CUSTOM_PRIORITY,
    ) -> None:
        self.exc_type = exc_type
        self.status = status
        self.category = category or category_for_status_code(status).value
        self.message = message
        self._priority = priority

    @property
    def priority(self) -> int:
        return self._priority

    def classify(self, exc: Exception) -> ClassifiedError | None:
        if not isinstance(exc, self.exc_type):
            return None
        if callable(self.message):
            text = self.message(exc)
        elif self.message is not None:
            text = self.message
        else:
            text = safe_str(exc)
        return ClassifiedError(
            category=self.category, status_code=self.status, message=text
        )


def register_classifier(classifier: ExceptionClassifier) -> ExceptionClassifier:
    """Register a classifier on every Errium engine in the process."""
    global _version
    _registered.append(classifier)
    _version += 1
    return classifier


def clear_registry() -> None:
    """Remove all globally registered classifiers (mainly for tests)."""
    global _version
    _registered.clear()
    _version += 1


def registered_classifiers() -> list[ExceptionClassifier]:
    return list(_registered)


def registry_version() -> int:
    return _version


def register(
    exc_type: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    *,
    status: int,
    category: str | None = None,
    message: str | Callable[[Exception], str] | None = None,
    priority: int = CUSTOM_PRIORITY,
) -> Callable[[T], T]:
    """Map an exception type to a status/category/message, on every adapter.

    Two forms::

        errium.register(OutOfStock, status=409, message="Item is out of stock.")

        @errium.register(status=409, category="CONFLICT")
        class OutOfStock(Exception): ...

    `category` defaults to the standard category for `status`; `message` may be
    a string or a callable taking the exception, and defaults to the
    exception's text (still sanitized for 5xx in production). Returns a
    decorator that leaves its target untouched.
    """

    def apply(target: Any) -> Any:
        register_classifier(
            ExceptionTypeClassifier(
                target,
                status=status,
                category=category,
                message=message,
                priority=priority,
            )
        )
        return target

    if exc_type is None:
        return apply

    apply(exc_type)
    return lambda target: target
