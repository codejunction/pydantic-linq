"""Projection: Select, SelectMany, Zip, Index.

Index-taking lambda overloads (``Select((x, i) => ...)``) are covered by ``index()``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any, overload

from ..base import EnumerableBase, defer, deferred

if TYPE_CHECKING:
    from ..enumerable import Enumerable


class Projection[T](EnumerableBase[T]):
    __slots__ = ()

    @deferred
    def select[U](self, selector: Callable[[T], U]) -> Iterator[U]:
        return map(selector, self)

    @overload
    def select_many[U](self, selector: Callable[[T], Iterable[U]]) -> Enumerable[U]: ...
    @overload
    def select_many[C, U](
        self, selector: Callable[[T], Iterable[C]], result_selector: Callable[[T, C], U]
    ) -> Enumerable[U]: ...
    def select_many(
        self, selector: Callable[[T], Iterable[Any]], result_selector: Callable[[T, Any], Any] | None = None
    ) -> Enumerable[Any]:
        def gen() -> Iterator[Any]:
            for x in self:
                for c in selector(x):
                    yield result_selector(x, c) if result_selector else c

        return defer(gen)

    @deferred
    def index(self) -> Iterator[tuple[int, T]]:
        """.NET 9 Index(): (index, element) pairs."""
        return enumerate(self)

    @overload
    def zip[S](self, second: Iterable[S], /) -> Enumerable[tuple[T, S]]: ...
    @overload
    def zip[S, U](self, second: Iterable[S], third: Iterable[U], /) -> Enumerable[tuple[T, S, U]]: ...
    def zip(self, *others: Iterable[Any]) -> Enumerable[tuple[Any, ...]]:
        return defer(lambda: zip(self, *others))

    @deferred
    def zip_with[S, R](self, second: Iterable[S], result_selector: Callable[[T, S], R]) -> Iterator[R]:
        """Zip(second, resultSelector)."""
        return map(result_selector, self, second)
