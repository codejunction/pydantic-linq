"""Grouping: GroupBy (yields AsyncGrouping), ToLookup (awaitable; returns the sync Lookup, like ToLookupAsync)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, overload

from ...sync.grouping import Lookup
from ..base import AsyncEnumerableBase, Fn, call, defer, group_async, wrap

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable
    from ..grouping import AsyncGrouping


class GroupingOps[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    @overload
    def group_by[K](self, key_selector: Fn[[T], K]) -> AsyncEnumerable[AsyncGrouping[K, T]]: ...
    @overload
    def group_by[K, E](
        self, key_selector: Fn[[T], K], element_selector: Fn[[T], E]
    ) -> AsyncEnumerable[AsyncGrouping[K, E]]: ...
    @overload
    def group_by[K, R](
        self, key_selector: Fn[[T], K], *, result_selector: Fn[[K, AsyncEnumerable[T]], R]
    ) -> AsyncEnumerable[R]: ...
    @overload
    def group_by[K, E, R](
        self,
        key_selector: Fn[[T], K],
        element_selector: Fn[[T], E],
        *,
        result_selector: Fn[[K, AsyncEnumerable[E]], R],
    ) -> AsyncEnumerable[R]: ...
    def group_by(
        self,
        key_selector: Fn[[T], Any],
        element_selector: Fn[[T], Any] | None = None,
        *,
        result_selector: Fn[[Any, AsyncEnumerable[Any]], Any] | None = None,
    ) -> AsyncEnumerable[Any]:
        from ..grouping import AsyncGrouping

        async def gen() -> AsyncIterator[Any]:
            for key, items in (await group_async(self, key_selector, element_selector)).items():
                yield await call(result_selector, key, wrap(items)) if result_selector else AsyncGrouping(key, items)

        return defer(gen)

    @overload
    async def to_lookup[K](self, key_selector: Fn[[T], K]) -> Lookup[K, T]: ...
    @overload
    async def to_lookup[K, E](self, key_selector: Fn[[T], K], element_selector: Fn[[T], E]) -> Lookup[K, E]: ...
    async def to_lookup(
        self, key_selector: Fn[[T], Any], element_selector: Fn[[T], Any] | None = None
    ) -> Lookup[Any, Any]:
        return Lookup(await group_async(self, key_selector, element_selector))
