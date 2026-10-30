"""Sorting: OrderBy, OrderByDescending, Order, OrderDescending, ThenBy, ThenByDescending, Reverse, Shuffle.

``comparer`` is an IComparer equivalent: ``cmp(a, b) -> int`` (negative, zero, positive).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Iterator
from functools import cmp_to_key
from typing import TYPE_CHECKING, Any

from ..base import EnumerableBase, deferred

if TYPE_CHECKING:
    from ..ordered import OrderedEnumerable

type Comparer = Callable[[Any, Any], int]
type SortKey[T] = tuple[Callable[[T], Any], Comparer | None, bool]


def _identity(x: Any) -> Any:
    return x


def sort[T](source: Iterable[T], keys: tuple[SortKey[T], ...]) -> list[T]:
    """Stable multi-key sort matching LINQ's composite comparison.

    Python's sort is stable (also with reverse=True), so sorting by the least significant key first is equivalent.
    """
    items = list(source)
    for key, comparer, descending in reversed(keys):
        if comparer is not None:
            to_key = cmp_to_key(comparer)
            items.sort(key=lambda x, key=key, to_key=to_key: to_key(key(x)), reverse=descending)
        else:
            items.sort(key=key, reverse=descending)
    return items


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
