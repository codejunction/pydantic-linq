"""Concatenation: Concat, Append, Prepend."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ..base import AnyIterable, AsyncEnumerableBase, deferred, iterate


class Concatenation[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @deferred
    async def concat(self, second: AnyIterable[T]) -> AsyncIterator[T]:
        async for x in self:
            yield x
        async for x in iterate(second):
            yield x

    @deferred
    async def append(self, element: T) -> AsyncIterator[T]:
        async for x in self:
            yield x
        yield element

    @deferred
    async def prepend(self, element: T) -> AsyncIterator[T]:
        yield element
        async for x in self:
            yield x
