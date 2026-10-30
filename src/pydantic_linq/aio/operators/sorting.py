"""Sorting: OrderBy, OrderByDescending, Order, OrderDescending, Reverse, Shuffle (ThenBy lives on the ordered type)."""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ...core.sorting import Comparer, identity
from ..base import AsyncEnumerableBase, Fn, deferred

if TYPE_CHECKING:
    from ..ordered import OrderedAsyncEnumerable


class Sorting[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    def order_by(self, key_selector: Fn[[T], Any], comparer: Comparer | None = None) -> OrderedAsyncEnumerable[T]:
        from ..ordered import OrderedAsyncEnumerable

        return OrderedAsyncEnumerable(self, ((key_selector, comparer, False),))

    def order_by_descending(
        self, key_selector: Fn[[T], Any], comparer: Comparer | None = None
    ) -> OrderedAsyncEnumerable[T]:
        from ..ordered import OrderedAsyncEnumerable

        return OrderedAsyncEnumerable(self, ((key_selector, comparer, True),))

    def order(self, comparer: Comparer | None = None) -> OrderedAsyncEnumerable[T]:
        return self.order_by(identity, comparer)

    def order_descending(self, comparer: Comparer | None = None) -> OrderedAsyncEnumerable[T]:
        return self.order_by_descending(identity, comparer)

    @deferred
    async def reverse(self) -> AsyncIterator[T]:
        for x in reversed(await self._list()):
            yield x

    @deferred
    async def shuffle(self) -> AsyncIterator[T]:
        items = await self._list()
        random.shuffle(items)
        for x in items:
            yield x
