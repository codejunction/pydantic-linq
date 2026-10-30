"""Sorting: OrderBy, OrderByDescending, Order, OrderDescending, ThenBy, ThenByDescending, Reverse, Shuffle.

``comparer`` is an IComparer equivalent: ``cmp(a, b) -> int`` (negative, zero, positive).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from ...core.sorting import Comparer
from ...core.sorting import identity as _identity
from ..base import EnumerableBase, deferred

if TYPE_CHECKING:
    from ..ordered import OrderedEnumerable

class Sorting[T](EnumerableBase[T]):
    __slots__ = ()

    def order_by(self, key_selector: Callable[[T], Any], comparer: Comparer | None = None) -> OrderedEnumerable[T]:
        from ..ordered import OrderedEnumerable

        return OrderedEnumerable(self, ((key_selector, comparer, False),))

    def order_by_descending(
        self, key_selector: Callable[[T], Any], comparer: Comparer | None = None
    ) -> OrderedEnumerable[T]:
        from ..ordered import OrderedEnumerable

        return OrderedEnumerable(self, ((key_selector, comparer, True),))

    def order(self, comparer: Comparer | None = None) -> OrderedEnumerable[T]:
        return self.order_by(_identity, comparer)

    def order_descending(self, comparer: Comparer | None = None) -> OrderedEnumerable[T]:
        return self.order_by_descending(_identity, comparer)

    @deferred
    def reverse(self) -> Iterator[T]:
        return reversed(list(self))

    @deferred
    def shuffle(self) -> Iterator[T]:
        """.NET 10 Shuffle."""
        items = list(self)
        random.shuffle(items)
        return iter(items)
