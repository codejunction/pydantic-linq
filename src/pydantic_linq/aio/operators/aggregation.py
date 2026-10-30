"""Aggregation (awaitable): Aggregate, AggregateBy, Count, CountBy, LongCount, Sum, Average, Min, Max, MinBy, MaxBy."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, overload

from ...core import MISSING, InvalidOperationError
from ...core.errors import NO_ELEMENTS
from ..base import AsyncEnumerableBase, Fn, call, defer

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


def _non_empty(value: Any) -> Any:
    if value is MISSING:
        raise InvalidOperationError(NO_ELEMENTS)
    return value


class Aggregation[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    async def _values(self, selector: Fn[[T], Any] | None) -> list[Any]:
        return [x if selector is None else await call(selector, x) async for x in self]

    async def count(self, predicate: Fn[[T], bool] | None = None) -> int:
        n = 0
        async for x in self:
            if predicate is None or await call(predicate, x):
                n += 1
        return n

    async def long_count(self, predicate: Fn[[T], bool] | None = None) -> int:
        return await self.count(predicate)

    async def sum(self, selector: Fn[[T], Any] | None = None) -> Any:
        return sum(await self._values(selector))

    async def average(self, selector: Fn[[T], Any] | None = None) -> float:
        values = await self._values(selector)
        if not values:
            raise InvalidOperationError(NO_ELEMENTS)
        return sum(values) / len(values)

    async def min(self, selector: Fn[[T], Any] | None = None) -> Any:
        return _non_empty(min(await self._values(selector), default=MISSING))

    async def max(self, selector: Fn[[T], Any] | None = None) -> Any:
        return _non_empty(max(await self._values(selector), default=MISSING))

    async def _keyed(self, key_selector: Fn[[T], Any]) -> list[tuple[Any, T]]:
        return [(await call(key_selector, x), x) async for x in self]

    async def min_by(self, key_selector: Fn[[T], Any]) -> T:
        return _non_empty(min(await self._keyed(key_selector), key=lambda p: p[0], default=(None, MISSING))[1])

    async def max_by(self, key_selector: Fn[[T], Any]) -> T:
        return _non_empty(max(await self._keyed(key_selector), key=lambda p: p[0], default=(None, MISSING))[1])

    @overload
    async def aggregate(self, func: Fn[[T, T], T], /) -> T: ...
    @overload
    async def aggregate[A](self, seed: A, func: Fn[[A, T], A], /) -> A: ...
    @overload
    async def aggregate[A, R](self, seed: A, func: Fn[[A, T], A], result_selector: Fn[[A], R], /) -> R: ...
    async def aggregate(self, *args: Any) -> Any:
        it = aiter(self)
        if len(args) == 1:
            func, acc = args[0], _non_empty(await anext(it, MISSING))
        else:
            acc, func = args[0], args[1]
        async for x in it:
            acc = await call(func, acc, x)
        return await call(args[2], acc) if len(args) == 3 else acc

    def aggregate_by[K, A](
        self, key_selector: Fn[[T], K], seed: A, func: Fn[[A, T], A]
    ) -> AsyncEnumerable[tuple[K, A]]:
        async def gen() -> AsyncIterator[tuple[K, A]]:
            acc: dict[K, A] = {}
            async for x in self:
                k = await call(key_selector, x)
                acc[k] = await call(func, acc.get(k, seed), x)
            for pair in acc.items():
                yield pair

        return defer(gen)

    def count_by[K](self, key_selector: Fn[[T], K]) -> AsyncEnumerable[tuple[K, int]]:
        return self.aggregate_by(key_selector, 0, lambda n, _: n + 1)
