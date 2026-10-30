"""Equality (awaitable): SequenceEqual."""

from __future__ import annotations

from ...core import MISSING
from ..base import AnyIterable, AsyncEnumerableBase, iterate


class Equality[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    async def sequence_equal(self, second: AnyIterable[T]) -> bool:
        a, b = aiter(self), iterate(second)
        while True:
            x, y = await anext(a, MISSING), await anext(b, MISSING)
            if x is MISSING or y is MISSING:
                return x is y
            if x != y:
                return False
