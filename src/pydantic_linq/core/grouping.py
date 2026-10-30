from collections.abc import Callable, Iterable, Iterator
from typing import Any


class Grouping[K, T](Iterable[T]):
    """IGrouping<TKey, TElement>."""

    __slots__ = ("key", "_items")

    def __init__(self, key: K, items: list[T]) -> None:
        self.key = key
        self._items = items

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"Grouping({self.key!r}, {self._items!r})"


def group[K, T, E](
    source: Iterable[T], key_selector: Callable[[T], K], element_selector: Callable[[T], E] | None = None
) -> dict[K, Grouping[K, E]]:
    """Group in first-seen key order, like GroupBy/ToLookup."""
    groups: dict[K, list[Any]] = {}
    for item in source:
        groups.setdefault(key_selector(item), []).append(element_selector(item) if element_selector else item)
    return {k: Grouping(k, v) for k, v in groups.items()}
