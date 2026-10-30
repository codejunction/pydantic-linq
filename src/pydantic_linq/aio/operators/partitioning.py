"""Partitioning: Take, Skip, TakeWhile, SkipWhile, TakeLast, SkipLast, Chunk."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from ..base import AsyncEnumerableBase, Fn, call, defer, deferred

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


class Partitioning[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    def take(self, count: int | slice) -> AsyncEnumerable[T]:
        """Take(int) or Take(Range): pass a slice for ranges; negative bounds count from the end (^n)."""
        s = count if isinstance(count, slice) else slice(max(count, 0))

        async def gen() -> AsyncIterator[T]:
            if any(b is not None and b < 0 for b in (s.start, s.stop)):
                for x in (await self._list())[s]:
                    yield x
                return
            start, stop, step = s.start or 0, s.stop, s.step or 1
            i = 0
            async for x in self:
                if stop is not None and i >= stop:
                    return
                if i >= start and (i - start) % step == 0:
                    yield x
                i += 1

        return defer(gen)

    @deferred
    async def skip(self, count: int) -> AsyncIterator[T]:
        i = 0
        async for x in self:
            if i >= count:
                yield x
            i += 1

    @deferred
    async def take_while(self, predicate: Fn[[T], bool]) -> AsyncIterator[T]:
        async for x in self:
            if not await call(predicate, x):
                return
            yield x

    @deferred
    async def skip_while(self, predicate: Fn[[T], bool]) -> AsyncIterator[T]:
        skipping = True
        async for x in self:
            if skipping and await call(predicate, x):
                continue
            skipping = False
            yield x

    @deferred
    async def take_last(self, count: int) -> AsyncIterator[T]:
        if count <= 0:
            return
        for x in deque([x async for x in self], maxlen=count):
            yield x

    @deferred
    async def skip_last(self, count: int) -> AsyncIterator[T]:
        buffer: deque[T] = deque()
        async for x in self:
            buffer.append(x)
            if len(buffer) > max(count, 0):
                yield buffer.popleft()

    def chunk(self, size: int) -> AsyncEnumerable[list[T]]:
        if size < 1:
            raise ValueError("size must be at least 1")

        async def gen() -> AsyncIterator[list[T]]:
            batch: list[T] = []
            async for x in self:
                batch.append(x)
                if len(batch) == size:
                    yield batch
                    batch = []
            if batch:
                yield batch

        return defer(gen)
