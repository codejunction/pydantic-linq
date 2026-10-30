"""Element operations: First, Last, Single, ElementAt and their *OrDefault variants."""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import Callable, Iterable
from typing import cast

from ...core import MISSING, InvalidOperationError
from ...core.errors import MORE_THAN_ONE, MORE_THAN_ONE_MATCH, NO_ELEMENTS, NO_MATCH
from ..base import EnumerableBase


class Element[T](EnumerableBase[T]):
    __slots__ = ()

    def _filtered(self, predicate: Callable[[T], bool] | None) -> Iterable[T]:
        return self if predicate is None else (x for x in self if predicate(x))

    @staticmethod
    def _missing(predicate: object) -> InvalidOperationError:
        return InvalidOperationError(NO_ELEMENTS if predicate is None else NO_MATCH)

    def first(self, predicate: Callable[[T], bool] | None = None) -> T:
        result = self.first_or_default(predicate, MISSING)
        if result is MISSING:
            raise self._missing(predicate)
        return cast(T, result)

    def first_or_default(self, predicate: Callable[[T], bool] | None = None, default: T | None = None) -> T | None:
        return next(iter(self._filtered(predicate)), default)

    def last(self, predicate: Callable[[T], bool] | None = None) -> T:
        result = self.last_or_default(predicate, MISSING)
        if result is MISSING:
            raise self._missing(predicate)
        return cast(T, result)

    def last_or_default(self, predicate: Callable[[T], bool] | None = None, default: T | None = None) -> T | None:
        tail = deque(self._filtered(predicate), maxlen=1)
        return tail[0] if tail else default

    def single(self, predicate: Callable[[T], bool] | None = None) -> T:
        result = self.single_or_default(predicate, MISSING)
        if result is MISSING:
            raise self._missing(predicate)
        return cast(T, result)

    def single_or_default(self, predicate: Callable[[T], bool] | None = None, default: T | None = None) -> T | None:
        it = iter(self._filtered(predicate))
        result = next(it, MISSING)
        if result is MISSING:
            return default
        if next(it, MISSING) is not MISSING:
            raise InvalidOperationError(MORE_THAN_ONE if predicate is None else MORE_THAN_ONE_MATCH)
        return result

    def element_at(self, index: int) -> T:
        """ElementAt(int) or ElementAt(Index): a negative index counts from the end (^n)."""
        result = self.element_at_or_default(index, MISSING)
        if result is MISSING:
            raise IndexError("Index was out of range")
        return cast(T, result)

    def element_at_or_default(self, index: int, default: T | None = None) -> T | None:
        if index < 0:
            tail = deque(self, maxlen=-index)
            return tail[0] if len(tail) == -index else default
        return next(itertools.islice(self, index, None), default)
