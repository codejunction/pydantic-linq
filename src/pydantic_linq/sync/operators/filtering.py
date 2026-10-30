"""Filtering: Where, OfType."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from ..base import EnumerableBase, deferred


class Filtering[T](EnumerableBase[T]):
    __slots__ = ()

    @deferred
    def where(self, predicate: Callable[[T], bool]) -> Iterator[T]:
        return (x for x in self if predicate(x))

    @deferred
    def of_type[U](self, type_: type[U]) -> Iterator[U]:
        return (x for x in self if isinstance(x, type_))
