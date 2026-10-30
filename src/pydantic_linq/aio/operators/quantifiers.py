"""Quantifiers (awaitable): Any, All, Contains."""

from __future__ import annotations

from ..base import AsyncEnumerableBase, Fn, call


class Quantifiers[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    async def any(self, predicate: Fn[[T], bool] | None = None) -> bool:
        async for x in self:
            if predicate is None or await call(predicate, x):
                return True
        return False

    async def all(self, predicate: Fn[[T], bool]) -> bool:
        async for x in self:
            if not await call(predicate, x):
                return False
        return True

    async def contains(self, value: T) -> bool:
        async for x in self:
            if x == value:
                return True
        return False
