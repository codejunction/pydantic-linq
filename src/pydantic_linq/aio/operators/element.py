"""Element operations (awaitable): First, Last, Single, ElementAt and their *OrDefault variants."""

from __future__ import annotations

from collections import deque
from typing import cast

from ...core import MISSING, InvalidOperationError
from ...core.errors import MORE_THAN_ONE, MORE_THAN_ONE_MATCH, NO_ELEMENTS, NO_MATCH
from ..base import AsyncEnumerableBase, Fn, call


def _missing(predicate: object) -> InvalidOperationError:
    return InvalidOperationError(NO_ELEMENTS if predicate is None else NO_MATCH)


class Element[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    async def first(self, predicate: Fn[[T], bool] | None = None) -> T:
        result = await self.first_or_default(predicate, MISSING)
        if result is MISSING:
            raise _missing(predicate)
        return cast(T, result)

    async def first_or_default(self, predicate: Fn[[T], bool] | None = None, default: T | None = None) -> T | None:
        async for x in self:
            if predicate is None or await call(predicate, x):
                return x
        return default

    async def last(self, predicate: Fn[[T], bool] | None = None) -> T:
        result = await self.last_or_default(predicate, MISSING)
        if result is MISSING:
            raise _missing(predicate)
        return cast(T, result)

    async def last_or_default(self, predicate: Fn[[T], bool] | None = None, default: T | None = None) -> T | None:
        result = default
        async for x in self:
            if predicate is None or await call(predicate, x):
                result = x
        return result

    async def single(self, predicate: Fn[[T], bool] | None = None) -> T:
        result = await self.single_or_default(predicate, MISSING)
        if result is MISSING:
            raise _missing(predicate)
        return cast(T, result)

    async def single_or_default(self, predicate: Fn[[T], bool] | None = None, default: T | None = None) -> T | None:
        result = MISSING
        async for x in self:
            if predicate is None or await call(predicate, x):
                if result is not MISSING:
                    raise InvalidOperationError(MORE_THAN_ONE if predicate is None else MORE_THAN_ONE_MATCH)
                result = x
        return default if result is MISSING else result

    async def element_at(self, index: int) -> T:
        """A negative index counts from the end (^n)."""
        result = await self.element_at_or_default(index, MISSING)
        if result is MISSING:
            raise IndexError("Index was out of range")
        return cast(T, result)

    async def element_at_or_default(self, index: int, default: T | None = None) -> T | None:
        if index < 0:
            tail = deque([x async for x in self], maxlen=-index)
            return tail[0] if len(tail) == -index else default
        i = 0
        async for x in self:
            if i == index:
                return x
            i += 1
        return default
