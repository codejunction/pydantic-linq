"""Generation: Empty, Range, Repeat, Sequence, InfiniteSequence, DefaultIfEmpty."""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from ..base import EnumerableBase, defer, deferred, wrap

if TYPE_CHECKING:
    from ..enumerable import Enumerable


class Generation[T](EnumerableBase[T]):
    __slots__ = ()

    @staticmethod
    def empty() -> Enumerable[Any]:
        return wrap(())

    @staticmethod
    def range(start: int, count: int) -> Enumerable[int]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return wrap(range(start, start + count))

    @staticmethod
    def repeat[U](element: U, count: int) -> Enumerable[U]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return defer(lambda: itertools.repeat(element, count))

    @staticmethod
    def sequence(start: int, end_inclusive: int, step: int) -> Enumerable[int]:
        """.NET 10 Enumerable.Sequence."""
        if step == 0:
            if start != end_inclusive:
                raise ValueError("step must be non-zero")
            return wrap((start,))
        if (step > 0 and end_inclusive < start) or (step < 0 and end_inclusive > start):
            raise ValueError("end_inclusive is unreachable from start with this step")
        return wrap(range(start, end_inclusive + (1 if step > 0 else -1), step))

    @staticmethod
    def infinite_sequence(start: int, step: int) -> Enumerable[int]:
        """.NET 10 Enumerable.InfiniteSequence."""
        return defer(lambda: itertools.count(start, step))

    @deferred
    def default_if_empty(self, default: T | None = None) -> Iterator[T | None]:
        empty = True
        for x in self:
            empty = False
            yield x
        if empty:
            yield default
