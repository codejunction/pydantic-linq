"""Base of the sync layer: the sequence wrapper every operator mixin builds on."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from .enumerable import Enumerable


class Defer[T]:
    """Re-enumerable iterable: calls the generator factory on every iteration (LINQ deferred execution)."""

    __slots__ = ("_factory",)

    def __init__(self, factory: Callable[[], Iterator[T]]) -> None:
        self._factory = factory

    def __iter__(self) -> Iterator[T]:
        return self._factory()


class EnumerableBase[T]:
    __slots__ = ("_source",)

    # Set by enumerable.py once the full class exists; lets mixins return Enumerable without a circular import.
    _create: ClassVar[Callable[[Iterable[Any]], Enumerable[Any]]]

    def __init__(self, source: Iterable[T] = ()) -> None:
        self._source = source

    def __iter__(self) -> Iterator[T]:
        return iter(self._source)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._source!r})"


def wrap[U](source: Iterable[U]) -> Enumerable[U]:
    return EnumerableBase._create(source)


def defer[U](factory: Callable[[], Iterator[U]]) -> Enumerable[U]:
    return wrap(Defer(factory))


def deferred[**P, U](fn: Callable[P, Iterator[U]]) -> Callable[P, Enumerable[U]]:
    """Turn a generator method into a deferred operator returning Enumerable."""

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Enumerable[U]:
        return defer(lambda: fn(*args, **kwargs))

    return wrapper
