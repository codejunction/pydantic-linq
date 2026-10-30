"""Set operations: Distinct, DistinctBy, Union, UnionBy, Intersect, IntersectBy, Except, ExceptBy.

Equality is value equality (==), so non-frozen pydantic models compare by field values.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any

from ...core import EqSet
from ..base import EnumerableBase, deferred

if TYPE_CHECKING:
    from ..enumerable import Enumerable


def _identity(x: Any) -> Any:
    return x


class Sets[T](EnumerableBase[T]):
    __slots__ = ()

    def distinct(self) -> Enumerable[T]:
        return self.distinct_by(_identity)

    @deferred
    def distinct_by(self, key_selector: Callable[[T], Any]) -> Iterator[T]:
        seen = EqSet()
        return (x for x in self if seen.add(key_selector(x)))

    def union(self, second: Iterable[T]) -> Enumerable[T]:
        return self.union_by(second, _identity)

    @deferred
    def union_by(self, second: Iterable[T], key_selector: Callable[[T], Any]) -> Iterator[T]:
        seen = EqSet()
        return (x for x in itertools.chain(self, second) if seen.add(key_selector(x)))

    def intersect(self, second: Iterable[T]) -> Enumerable[T]:
        return self.intersect_by(second, _identity)

    @deferred
    def intersect_by[K](self, second: Iterable[K], key_selector: Callable[[T], K]) -> Iterator[T]:
        keys = EqSet(second)
        return (x for x in self if keys.remove(key_selector(x)))

    def except_(self, second: Iterable[T]) -> Enumerable[T]:
        """Except (trailing underscore: ``except`` is a keyword)."""
        return self.except_by(second, _identity)

    @deferred
    def except_by[K](self, second: Iterable[K], key_selector: Callable[[T], K]) -> Iterator[T]:
        seen = EqSet(second)
        return (x for x in self if seen.add(key_selector(x)))
