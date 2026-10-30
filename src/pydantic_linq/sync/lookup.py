from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from ..core import Grouping
from .base import wrap

if TYPE_CHECKING:
    from .enumerable import Enumerable


class Lookup[K, T](Iterable[Grouping[K, T]]):
    """ILookup<TKey, TElement>: a missing key yields an empty sequence instead of raising."""

    __slots__ = ("_groups",)

    def __init__(self, groups: dict[K, Grouping[K, T]]) -> None:
        self._groups = groups

    def __getitem__(self, key: K) -> Enumerable[T]:
        group = self._groups.get(key)
        return wrap(group if group is not None else ())

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
