"""Join operations: Join, GroupJoin, LeftJoin, RightJoin."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from ..base import (
    AnyIterable,
    AsyncEnumerableBase,
    Fn,
    call,
    deferred,
    group_async,
    iterate,
    wrap,
)

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


class Joining[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @deferred
    async def join[I, K, R](
        self,
        inner: AnyIterable[I],
        outer_key_selector: Fn[[T], K],
        inner_key_selector: Fn[[I], K],
        result_selector: Fn[[T, I], R],
    ) -> AsyncIterator[R]:
        lookup = await group_async(inner, inner_key_selector)
        async for x in self:
            for i in lookup.get(await call(outer_key_selector, x), ()):
                yield await call(result_selector, x, i)

    @deferred
    async def group_join[I, K, R](
        self,
        inner: AnyIterable[I],
        outer_key_selector: Fn[[T], K],
        inner_key_selector: Fn[[I], K],
        result_selector: Fn[[T, AsyncEnumerable[I]], R],
    ) -> AsyncIterator[R]:
        lookup = await group_async(inner, inner_key_selector)
        async for x in self:
            yield await call(result_selector, x, wrap(lookup.get(await call(outer_key_selector, x), ())))

    @deferred
    async def left_join[I, K, R](
        self,
        inner: AnyIterable[I],
        outer_key_selector: Fn[[T], K],
        inner_key_selector: Fn[[I], K],
        result_selector: Fn[[T, I | None], R],
    ) -> AsyncIterator[R]:
        """Unmatched outer elements pair with None."""
        lookup = await group_async(inner, inner_key_selector)
        async for x in self:
            matches = lookup.get(await call(outer_key_selector, x))
            for i in matches if matches is not None else (None,):
                yield await call(result_selector, x, i)

    @deferred
    async def right_join[I, K, R](
        self,
        inner: AnyIterable[I],
        outer_key_selector: Fn[[T], K],
        inner_key_selector: Fn[[I], K],
        result_selector: Fn[[T | None, I], R],
    ) -> AsyncIterator[R]:
        """Unmatched inner elements pair with None."""
        lookup = await group_async(self, outer_key_selector)
        async for i in iterate(inner):
            matches = lookup.get(await call(inner_key_selector, i))
            for x in matches if matches is not None else (None,):
                yield await call(result_selector, x, i)
