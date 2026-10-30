"""Conversion: AsAsyncEnumerable, Cast, ToList, ToArray, ToHashSet, ToDictionary (terminal ones are awaitable)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, overload

from pydantic import TypeAdapter

from ..base import AsyncEnumerableBase, Fn, call, deferred

if TYPE_CHECKING:
    from typing import Self


class Conversion[T](AsyncEnumerableBase[T]):
    __slots__ = ()

    def as_async_enumerable(self) -> Self:
        return self

    @deferred
    async def cast[U](self, type_: type[U], *, strict: bool = False) -> AsyncIterator[U]:
        """Cast<T>, pydantic-style: validates each element with a TypeAdapter (dicts become models)."""
        adapter = TypeAdapter(type_)
        async for x in self:
            yield adapter.validate_python(x, strict=strict)

    async def to_list(self) -> list[T]:
        return await self._list()

    async def to_array(self) -> list[T]:
        return await self._list()

    async def to_hash_set(self) -> set[T]:
        return set(await self._list())

    @overload
    async def to_dictionary[K](self, key_selector: Fn[[T], K]) -> dict[K, T]: ...
    @overload
    async def to_dictionary[K, E](self, key_selector: Fn[[T], K], element_selector: Fn[[T], E]) -> dict[K, E]: ...
    async def to_dictionary(
        self, key_selector: Fn[[T], Any], element_selector: Fn[[T], Any] | None = None
    ) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        async for x in self:
            k = await call(key_selector, x)
            if k in result:
                raise ValueError(f"An item with the same key has already been added. Key: {k!r}")
            result[k] = await call(element_selector, x) if element_selector else x
        return result
