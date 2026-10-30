"""Quantifiers: Any, All, Contains."""

from __future__ import annotations

from collections.abc import Callable

from ...core import MISSING
from ..base import EnumerableBase


class Quantifiers[T](EnumerableBase[T]):
    __slots__ = ()

    def any(self, predicate: Callable[[T], bool] | None = None) -> bool:
        if predicate is None:
            return next(iter(self), MISSING) is not MISSING
        return any(predicate(x) for x in self)

    def all(self, predicate: Callable[[T], bool]) -> bool:
        return all(predicate(x) for x in self)

    def contains(self, value: T) -> bool:
        return any(x == value for x in self)
