from __future__ import annotations

from collections.abc import Iterable, Iterator

from .enumerable import Enumerable


class Grouping[K, T](Enumerable[T]):
    """IGrouping<TKey, TElement>: a keyed Enumerable."""

    __slots__ = ("key",)

    def __init__(self, key: K, items: list[T]) -> None:
        super().__init__(items)
        self.key = key

    def __len__(self) -> int:
        return len(self._source)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return f"Grouping({self.key!r}, {self._source!r})"


class Lookup[K, T](Iterable[Grouping[K, T]]):
    """ILookup<TKey, TElement>: a missing key yields an empty sequence instead of raising."""

    __slots__ = ("_groups",)

    def __init__(self, groups: dict[K, list[T]]) -> None:
        self._groups = {k: Grouping(k, v) for k, v in groups.items()}

    def __getitem__(self, key: K) -> Enumerable[T]:
        return self._groups.get(key) or Enumerable(())

    def __contains__(self, key: object) -> bool:
        return key in self._groups

    def contains(self, key: K) -> bool:
        return key in self._groups

    @property
    def count(self) -> int:
        return len(self._groups)

    def __len__(self) -> int:
        return len(self._groups)

    def __iter__(self) -> Iterator[Grouping[K, T]]:
        return iter(self._groups.values())
