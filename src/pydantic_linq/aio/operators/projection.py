"""Projection: Select, SelectMany, Index, Zip."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, overload

from ...core import MISSING
from ..base import AnyIterable, AsyncEnumerableBase, Fn, call, defer, deferred, iterate

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


class Projection[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @deferred
    async def select[U](self, selector: Fn[[T], U]) -> AsyncIterator[U]:
        async for x in self:
            yield await call(selector, x)

    @overload
    def select_many[U](self, selector: Fn[[T], AnyIterable[U]]) -> AsyncEnumerable[U]: ...
    @overload
    def select_many[C, U](
        self, selector: Fn[[T], AnyIterable[C]], result_selector: Fn[[T, C], U]
    ) -> AsyncEnumerable[U]: ...
    def select_many(
        self, selector: Fn[[T], AnyIterable[Any]], result_selector: Fn[[T, Any], Any] | None = None
    ) -> AsyncEnumerable[Any]:
        async def gen() -> AsyncIterator[Any]:
            async for x in self:
                async for c in iterate(await call(selector, x)):
                    yield await call(result_selector, x, c) if result_selector else c

        return defer(gen)

    @deferred
    async def index(self) -> AsyncIterator[tuple[int, T]]:
        i = 0
        async for x in self:
            yield i, x
            i += 1

    @overload
    def zip[S](self, second: AnyIterable[S], /) -> AsyncEnumerable[tuple[T, S]]: ...
    @overload
    def zip[S, U](self, second: AnyIterable[S], third: AnyIterable[U], /) -> AsyncEnumerable[tuple[T, S, U]]: ...
    def zip(self, *others: AnyIterable[Any]) -> AsyncEnumerable[tuple[Any, ...]]:
        async def gen() -> AsyncIterator[tuple[Any, ...]]:
            iterators = [aiter(self), *(iterate(o) for o in others)]
            while True:
                row = [await anext(it, MISSING) for it in iterators]
                if any(v is MISSING for v in row):
                    return
                yield tuple(row)

        return defer(gen)

    @deferred
    async def zip_with[S, R](self, second: AnyIterable[S], result_selector: Fn[[T, S], R]) -> AsyncIterator[R]:
        async for a, b in self.zip(second):
            yield await call(result_selector, a, b)
