"""Adds the LINQ operators to list, tuple, set and frozenset (via forbiddenfruit), so ``rows.select(...)`` works.

Names a builtin already defines (list.count, list.index, list.reverse, list.append, set.union, ...) keep
their Python meaning; use ``rows.as_enumerable().count()`` for the LINQ version.
Type checkers can't see patched methods; use ``Enumerable(rows)`` where static typing matters.
"""

import inspect
from collections.abc import Callable
from typing import Any

from forbiddenfruit import curse, reverse

from ..sync.enumerable import Enumerable

TARGETS: tuple[type, ...] = (list, tuple, set, frozenset)

_installed: dict[type, list[str]] = {}


def _operator_names() -> list[str]:
    return [
        name
        for name in dir(Enumerable)
        if not name.startswith("_") and not isinstance(inspect.getattr_static(Enumerable, name), staticmethod)
    ]


def _proxy(name: str) -> Callable[..., Any]:
    def method(self: Any, *args: Any, **kwargs: Any) -> Any:
        return getattr(Enumerable(self), name)(*args, **kwargs)

    method.__name__ = name
    method.__doc__ = getattr(Enumerable, name).__doc__
    return method


def install() -> None:
    """Patch the builtin collections. Idempotent; runs on ``import pydantic_linq``."""
    for target in TARGETS:
        if target in _installed:
            continue
        names = [n for n in _operator_names() if not hasattr(target, n)]
        for name in names:
            curse(target, name, _proxy(name))
        _installed[target] = names


def uninstall() -> None:
    """Remove every method install() added."""
    for target, names in _installed.items():
        for name in names:
            reverse(target, name)
    _installed.clear()
