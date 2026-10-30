from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from .enumerable import Enumerable
from .operators.sorting import Comparer, SortKey, sort


class OrderedEnumerable[T](Enumerable[T]):
    """IOrderedEnumerable<T>: stable multi-key sort; supports then_by / then_by_descending."""

    __slots__ = ("_keys",)

    def __init__(self, source: Iterable[T], keys: tuple[SortKey[T], ...]) -> None:
        super().__init__(source)
        self._keys = keys

    def __iter__(self) -> Iterator[T]:
        return iter(sort(self._source, self._keys))

    def then_by(self, key_selector: Callable[[T], Any], comparer: Comparer | None = None) -> OrderedEnumerable[T]:
        return OrderedEnumerable(self._source, (*self._keys, (key_selector, comparer, False)))

    def then_by_descending(
        self, key_selector: Callable[[T], Any], comparer: Comparer | None = None
    ) -> OrderedEnumerable[T]:
        return OrderedEnumerable(self._source, (*self._keys, (key_selector, comparer, True)))
