"""Aggregation: Aggregate, AggregateBy, Count, CountBy, LongCount, TryGetNonEnumeratedCount,
Sum, Average, Min, Max, MinBy, MaxBy.

Min/Max/MinBy/MaxBy/Average on an empty sequence raise InvalidOperationError (the .NET value-type behavior).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sized
from typing import TYPE_CHECKING, Any, overload

from ...core import MISSING, InvalidOperationError
from ...core.errors import NO_ELEMENTS
from ..base import EnumerableBase, defer

if TYPE_CHECKING:
    from ..enumerable import Enumerable


class Aggregation[T](EnumerableBase[T]):
    __slots__ = ()

    def _values(self, selector: Callable[[T], Any] | None) -> Iterable[Any]:
        return self if selector is None else map(selector, self)

    def count(self, predicate: Callable[[T], bool] | None = None) -> int:
        if predicate is None:
            n = self.try_get_non_enumerated_count()
            return n if n is not None else sum(1 for _ in self)
        return sum(1 for x in self if predicate(x))

    def long_count(self, predicate: Callable[[T], bool] | None = None) -> int:
        return self.count(predicate)

    def try_get_non_enumerated_count(self) -> int | None:
        return len(self._source) if isinstance(self._source, Sized) else None

    def sum(self, selector: Callable[[T], Any] | None = None) -> Any:
        return sum(self._values(selector))

    def average(self, selector: Callable[[T], Any] | None = None) -> float:
        total: Any = 0
        n = 0
        for x in self._values(selector):
            total += x
            n += 1
        if n == 0:
            raise InvalidOperationError(NO_ELEMENTS)
        return total / n

    def min(self, selector: Callable[[T], Any] | None = None) -> Any:
        return _non_empty(min(self._values(selector), default=MISSING))

    def max(self, selector: Callable[[T], Any] | None = None) -> Any:
        return _non_empty(max(self._values(selector), default=MISSING))

    def min_by(self, key_selector: Callable[[T], Any]) -> T:
        return _non_empty(min(self, key=key_selector, default=MISSING))

    def max_by(self, key_selector: Callable[[T], Any]) -> T:
        return _non_empty(max(self, key=key_selector, default=MISSING))

    @overload
    def aggregate(self, func: Callable[[T, T], T], /) -> T: ...
    @overload
    def aggregate[A](self, seed: A, func: Callable[[A, T], A], /) -> A: ...
    @overload
    def aggregate[A, R](self, seed: A, func: Callable[[A, T], A], result_selector: Callable[[A], R], /) -> R: ...
    def aggregate(self, *args: Any) -> Any:
        it = iter(self)
        if len(args) == 1:
            func, acc = args[0], _non_empty(next(it, MISSING))
        else:
            acc, func = args[0], args[1]
        for x in it:
            acc = func(acc, x)
        return args[2](acc) if len(args) == 3 else acc

    def aggregate_by[K, A](
        self, key_selector: Callable[[T], K], seed: A, func: Callable[[A, T], A]
    ) -> Enumerable[tuple[K, A]]:
        """.NET 9 AggregateBy; yields (key, accumulate) tuples in place of KeyValuePair."""

        def gen() -> Iterator[tuple[K, A]]:
            acc: dict[K, A] = {}
            for x in self:
                k = key_selector(x)
                acc[k] = func(acc.get(k, seed), x)
            return iter(acc.items())

        return defer(gen)

    def count_by[K](self, key_selector: Callable[[T], K]) -> Enumerable[tuple[K, int]]:
        """.NET 9 CountBy."""
        return self.aggregate_by(key_selector, 0, lambda n, _: n + 1)


def _non_empty(value: Any) -> Any:
    if value is MISSING:
        raise InvalidOperationError(NO_ELEMENTS)
    return value
