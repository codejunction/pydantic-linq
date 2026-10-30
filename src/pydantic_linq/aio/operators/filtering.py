"""Filtering: Where, OfType."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ..base import AsyncEnumerableBase, Fn, call, deferred


class Filtering[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @deferred
    async def where(self, predicate: Fn[[T], bool]) -> AsyncIterator[T]:
        async for x in self:
            if await call(predicate, x):
                yield x

    @deferred
    async def of_type[U](self, type_: type[U]) -> AsyncIterator[U]:
        async for x in self:
            if isinstance(x, type_):
                yield x
