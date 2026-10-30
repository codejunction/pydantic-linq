from collections.abc import Callable, Iterable
from typing import Any


def group[K, T, E](
    source: Iterable[T], key_selector: Callable[[T], K], element_selector: Callable[[T], E] | None = None
) -> dict[K, list[E]]:
    """Group in first-seen key order, like GroupBy/ToLookup. Each layer wraps the lists in its own Grouping."""
    groups: dict[K, list[Any]] = {}
    for item in source:
        groups.setdefault(key_selector(item), []).append(element_selector(item) if element_selector else item)
    return groups
