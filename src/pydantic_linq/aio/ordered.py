from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ..core.sorting import Comparer, sort
from .base import AnyIterable, Fn, call
from .enumerable import AsyncEnumerable

type AsyncSortKey[T] = tuple[Fn[[T], Any], Comparer | None, bool]


class OrderedAsyncEnumerable[T](AsyncEnumerable[T]):
    """IOrderedAsyncEnumerable<T>: stable multi-key sort; supports then_by / then_by_descending."""

    __slots__ = ("_keys",)

    def __init__(self, source: AnyIterable[T], keys: tuple[AsyncSortKey[T], ...]) -> None:
        super().__init__(source)
        self._keys = keys

    async def _sorted(self) -> AsyncIterator[T]:
        # Resolve every (possibly async) key once, then reuse the sync stable sort on the key tuples.
        rows = [([await call(k, x) for k, _, _ in self._keys], x) async for x in super().__aiter__()]
        keys = tuple((lambda r, i=i: r[0][i], comparer, desc) for i, (_, comparer, desc) in enumerate(self._keys))
        for _, x in sort(rows, keys):
            yield x

    def __aiter__(self) -> AsyncIterator[T]:
        return self._sorted()

    def then_by(self, key_selector: Fn[[T], Any], comparer: Comparer | None = None) -> OrderedAsyncEnumerable[T]:
        return OrderedAsyncEnumerable(self._source, (*self._keys, (key_selector, comparer, False)))

    def then_by_descending(
        self, key_selector: Fn[[T], Any], comparer: Comparer | None = None
    ) -> OrderedAsyncEnumerable[T]:
        return OrderedAsyncEnumerable(self._source, (*self._keys, (key_selector, comparer, True)))
