"""Stable multi-key sort shared by the sync and async OrderBy/ThenBy."""

from collections.abc import Callable, Iterable
from functools import cmp_to_key
from typing import Any

type Comparer = Callable[[Any, Any], int]
"""IComparer equivalent: ``cmp(a, b) -> int`` (negative, zero, positive)."""
type SortKey[T] = tuple[Callable[[T], Any], Comparer | None, bool]


def identity(x: Any) -> Any:
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
