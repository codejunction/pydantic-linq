"""Concatenation: Concat, Append, Prepend."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator

from ..base import EnumerableBase, deferred


class Concatenation[T](EnumerableBase[T]):
    __slots__ = ()

    @deferred
    def concat(self, second: Iterable[T]) -> Iterator[T]:
        return itertools.chain(self, second)

    @deferred
    def append(self, element: T) -> Iterator[T]:
        return itertools.chain(self, (element,))

    @deferred
    def prepend(self, element: T) -> Iterator[T]:
        return itertools.chain((element,), self)
