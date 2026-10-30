"""Join operations: Join, GroupJoin, LeftJoin, RightJoin (.NET 10)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING

from ...core import group
from ..base import EnumerableBase, deferred, wrap

if TYPE_CHECKING:
    from ..enumerable import Enumerable


class Joining[T](EnumerableBase[T]):
    __slots__ = ()

    @deferred
    def join[I, K, R](
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T, I], R],
    ) -> Iterator[R]:
        lookup = group(inner, inner_key_selector)
        for x in self:
            for i in lookup.get(outer_key_selector(x), ()):
                yield result_selector(x, i)

    @deferred
    def group_join[I, K, R](
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T, Enumerable[I]], R],
    ) -> Iterator[R]:
        lookup = group(inner, inner_key_selector)
        for x in self:
            yield result_selector(x, wrap(lookup.get(outer_key_selector(x), ())))

    @deferred
    def left_join[I, K, R](
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T, I | None], R],
    ) -> Iterator[R]:
        """Unmatched outer elements pair with None."""
        lookup = group(inner, inner_key_selector)
        for x in self:
            matches = lookup.get(outer_key_selector(x))
            if matches is None:
                yield result_selector(x, None)
            else:
                for i in matches:
                    yield result_selector(x, i)

    @deferred
    def right_join[I, K, R](
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T | None, I], R],
    ) -> Iterator[R]:
        """Unmatched inner elements pair with None."""
        lookup = group(self, outer_key_selector)
        for i in inner:
            matches = lookup.get(inner_key_selector(i))
            if matches is None:
                yield result_selector(None, i)
            else:
                for x in matches:
                    yield result_selector(x, i)
