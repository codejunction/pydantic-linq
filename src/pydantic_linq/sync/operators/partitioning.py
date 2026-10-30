"""Partitioning: Take, Skip, TakeWhile, SkipWhile, TakeLast, SkipLast, Chunk."""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from ..base import EnumerableBase, defer, deferred

if TYPE_CHECKING:
    from ..enumerable import Enumerable


class Partitioning[T](EnumerableBase[T]):
    __slots__ = ()

    def take(self, count: int | slice) -> Enumerable[T]:
        """Take(int) or Take(Range): pass a slice for ranges; negative bounds count from the end (^n)."""
        if isinstance(count, slice):
            s = count
            if any(b is not None and b < 0 for b in (s.start, s.stop)):
                return defer(lambda: iter(list(self)[s]))
            return defer(lambda: itertools.islice(self, s.start, s.stop, s.step))
        return defer(lambda: itertools.islice(self, max(count, 0)))

    @deferred
    def skip(self, count: int) -> Iterator[T]:
        return itertools.islice(self, max(count, 0), None)

    @deferred
    def take_while(self, predicate: Callable[[T], bool]) -> Iterator[T]:
        return itertools.takewhile(predicate, self)

    @deferred
    def skip_while(self, predicate: Callable[[T], bool]) -> Iterator[T]:
        return itertools.dropwhile(predicate, self)

    @deferred
    def take_last(self, count: int) -> Iterator[T]:
        return iter(deque(self, maxlen=count)) if count > 0 else iter(())

    @deferred
    def skip_last(self, count: int) -> Iterator[T]:
        if count <= 0:
            yield from self
            return
        buffer: deque[T] = deque()
        for x in self:
            buffer.append(x)
            if len(buffer) > count:
                yield buffer.popleft()

    def chunk(self, size: int) -> Enumerable[list[T]]:
        if size < 1:
            raise ValueError("size must be at least 1")

        def gen() -> Iterator[list[T]]:
            it = iter(self)
            while batch := list(itertools.islice(it, size)):
                yield batch

        return defer(gen)
