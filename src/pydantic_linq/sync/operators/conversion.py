"""Conversion: AsEnumerable, Cast, ToList, ToArray, ToHashSet, ToDictionary."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, overload

from pydantic import TypeAdapter

from ..base import EnumerableBase, deferred

if TYPE_CHECKING:
    from typing import Self


class Conversion[T](EnumerableBase[T]):
    __slots__ = ()

    def as_enumerable(self) -> Self:
        return self

    @deferred
    def cast[U](self, type_: type[U], *, strict: bool = False) -> Iterator[U]:
        """Cast<T>, pydantic-style: validates each element with a TypeAdapter (dicts become models)."""
        adapter = TypeAdapter(type_)
        return (adapter.validate_python(x, strict=strict) for x in self)

    def to_list(self) -> list[T]:
        return list(self)

    def to_array(self) -> list[T]:
        return list(self)

    def to_hash_set(self) -> set[T]:
        return set(self)

    @overload
    def to_dictionary[K](self, key_selector: Callable[[T], K]) -> dict[K, T]: ...
    @overload
    def to_dictionary[K, E](self, key_selector: Callable[[T], K], element_selector: Callable[[T], E]) -> dict[K, E]: ...
    def to_dictionary(
        self, key_selector: Callable[[T], Any], element_selector: Callable[[T], Any] | None = None
    ) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for x in self:
            k = key_selector(x)
            if k in result:
                raise ValueError(f"An item with the same key has already been added. Key: {k!r}")
            result[k] = element_selector(x) if element_selector else x
        return result
