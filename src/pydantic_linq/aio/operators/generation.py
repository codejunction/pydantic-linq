"""Generation: Empty, Range, Repeat, DefaultIfEmpty."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ..base import AsyncEnumerableBase, deferred, wrap

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


class Generation[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @staticmethod
    def empty() -> AsyncEnumerable[Any]:
        return wrap(())

    @staticmethod
    def range(start: int, count: int) -> AsyncEnumerable[int]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return wrap(range(start, start + count))

    @staticmethod
    def repeat[U](element: U, count: int) -> AsyncEnumerable[U]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return wrap([element] * count)

    @deferred
    async def default_if_empty(self, default: T | None = None) -> AsyncIterator[T | None]:
        empty = True
        async for x in self:
            empty = False
            yield x
        if empty:
            yield default
