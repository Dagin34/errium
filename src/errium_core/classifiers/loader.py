from importlib import import_module
from typing import Any

from errium_core.classifiers.base import ExceptionClassifier


def load_classifiers(specs: list[Any] | tuple[Any, ...]) -> list[ExceptionClassifier]:
    """Resolve classifier specs: instances, classes, or dotted-path strings.

    A string `"package.module.ClassName"` is imported; a class is instantiated
    with no arguments.
    """
    loaded: list[ExceptionClassifier] = []
    for spec in specs:
        target = spec
        if isinstance(spec, str):
            module_path, _, attribute = spec.rpartition(".")
            if not module_path:
                raise ImportError(f"'{spec}' is not a dotted path to a classifier")
            target = getattr(import_module(module_path), attribute)
        loaded.append(target() if isinstance(target, type) else target)
    return loaded
