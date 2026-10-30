"""Set operations: Distinct, DistinctBy, Union, UnionBy, Intersect, IntersectBy, Except, ExceptBy."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ...core import EqSet
from ...core.sorting import identity
from ..base import AnyIterable, AsyncEnumerableBase, Fn, call, deferred, iterate

if TYPE_CHECKING:
    from ..enumerable import AsyncEnumerable


class Sets[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    def distinct(self) -> AsyncEnumerable[T]:
        return self.distinct_by(identity)

    @deferred
    async def distinct_by(self, key_selector: Fn[[T], Any]) -> AsyncIterator[T]:
        seen = EqSet()
        async for x in self:
            if seen.add(await call(key_selector, x)):
                yield x

    def union(self, second: AnyIterable[T]) -> AsyncEnumerable[T]:
        return self.union_by(second, identity)

    @deferred
    async def union_by(self, second: AnyIterable[T], key_selector: Fn[[T], Any]) -> AsyncIterator[T]:
        seen = EqSet()
        for source in (self, second):
            async for x in iterate(source):
                if seen.add(await call(key_selector, x)):
                    yield x

    def intersect(self, second: AnyIterable[T]) -> AsyncEnumerable[T]:
        return self.intersect_by(second, identity)

    @deferred
    async def intersect_by[K](self, second: AnyIterable[K], key_selector: Fn[[T], K]) -> AsyncIterator[T]:
        keys = EqSet([k async for k in iterate(second)])
        async for x in self:
            if keys.remove(await call(key_selector, x)):
                yield x

    def except_(self, second: AnyIterable[T]) -> AsyncEnumerable[T]:
        """Except (trailing underscore: ``except`` is a keyword)."""
        return self.except_by(second, identity)

    @deferred
    async def except_by[K](self, second: AnyIterable[K], key_selector: Fn[[T], K]) -> AsyncIterator[T]:
        seen = EqSet([k async for k in iterate(second)])
        async for x in self:
            if seen.add(await call(key_selector, x)):
                yield x
