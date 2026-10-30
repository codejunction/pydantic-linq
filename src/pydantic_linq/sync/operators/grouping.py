"""Grouping: GroupBy, ToLookup."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, overload

from ...core import group
from ..base import EnumerableBase, defer, wrap

if TYPE_CHECKING:
    from ..enumerable import Enumerable
    from ..grouping import Grouping, Lookup


class GroupingOps[T](EnumerableBase[T]):
    __slots__ = ()

    @overload
    def group_by[K](self, key_selector: Callable[[T], K]) -> Enumerable[Grouping[K, T]]: ...
    @overload
    def group_by[K, E](
        self, key_selector: Callable[[T], K], element_selector: Callable[[T], E]
    ) -> Enumerable[Grouping[K, E]]: ...
    @overload
    def group_by[K, E, R](
        self,
        key_selector: Callable[[T], K],
        element_selector: Callable[[T], E] | None = None,
        *,
        result_selector: Callable[[K, Enumerable[E]], R],
    ) -> Enumerable[R]: ...
    def group_by(
        self,
        key_selector: Callable[[T], Any],
        element_selector: Callable[[T], Any] | None = None,
        *,
        result_selector: Callable[[Any, Enumerable[Any]], Any] | None = None,
    ) -> Enumerable[Any]:
        from ..grouping import Grouping

        def gen() -> Iterator[Any]:
            for key, items in group(self, key_selector, element_selector).items():
                yield result_selector(key, wrap(items)) if result_selector else Grouping(key, items)

        return defer(gen)

    @overload
    def to_lookup[K](self, key_selector: Callable[[T], K]) -> Lookup[K, T]: ...
    @overload
    def to_lookup[K, E](self, key_selector: Callable[[T], K], element_selector: Callable[[T], E]) -> Lookup[K, E]: ...
    def to_lookup(
        self, key_selector: Callable[[T], Any], element_selector: Callable[[T], Any] | None = None
    ) -> Lookup[Any, Any]:
        from ..grouping import Lookup

        return Lookup(group(self, key_selector, element_selector))
