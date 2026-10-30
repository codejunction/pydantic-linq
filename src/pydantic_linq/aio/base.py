"""Base of the async layer: the async sequence wrapper every async operator mixin builds on.

Every selector / predicate may be a plain function or return an awaitable (``async def``), which
covers both the System.Linq.Async ``*Await`` overloads and the .NET 10 ``AsyncEnumerable`` ones.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Iterable
from functools import wraps
from operator import itemgetter
from typing import TYPE_CHECKING, Any, ClassVar

from ..core import group

if TYPE_CHECKING:
    from .enumerable import AsyncEnumerable

type Fn[**P, R] = Callable[P, R | Awaitable[R]]
"""A callable that is sync or async."""

type AnyIterable[T] = AsyncIterable[T] | Iterable[T]


async def call[R](fn: Callable[..., R | Awaitable[R]], *args: Any) -> R:
    result = fn(*args)
    return await result if inspect.isawaitable(result) else result  # type: ignore[return-value]


async def iterate[T](source: AnyIterable[T]) -> AsyncIterator[T]:
    """Async-iterate a sync or async iterable."""
    if isinstance(source, AsyncIterable):
        async for x in source:
            yield x
    else:
        for x in source:
            yield x


async def group_async[K, T, E](
    source: AnyIterable[T], key_selector: Fn[[T], K], element_selector: Fn[[T], E] | None = None
) -> dict[K, list[E]]:
    """core.group with sync-or-async selectors."""
    pairs = [
        (await call(key_selector, x), await call(element_selector, x) if element_selector else x)
        async for x in iterate(source)
    ]
    return group(pairs, itemgetter(0), itemgetter(1))


class ADefer[T]:
    """Re-enumerable async iterable: calls the async generator factory on every iteration."""

    __slots__ = ("_factory",)

    def __init__(self, factory: Callable[[], AsyncIterator[T]]) -> None:
        self._factory = factory

    def __aiter__(self) -> AsyncIterator[T]:
        return self._factory()


class AsyncEnumerableBase[T]:
    __slots__ = ("_source",)

    _create: ClassVar[Callable[[AnyIterable[Any]], AsyncEnumerable[Any]]]

    def __init__(self, source: AnyIterable[T] = ()) -> None:
        self._source = source

    def __aiter__(self) -> AsyncIterator[T]:
        return iterate(self._source)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._source!r})"

    async def _list(self) -> list[T]:
        return [x async for x in self]


def wrap[U](source: AnyIterable[U]) -> AsyncEnumerable[U]:
    return AsyncEnumerableBase._create(source)


def defer[U](factory: Callable[[], AsyncIterator[U]]) -> AsyncEnumerable[U]:
    return wrap(ADefer(factory))


def deferred[**P, U](fn: Callable[P, AsyncIterator[U]]) -> Callable[P, AsyncEnumerable[U]]:
    """Turn an async generator method into a deferred operator returning AsyncEnumerable."""

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> AsyncEnumerable[U]:
        return defer(lambda: fn(*args, **kwargs))

    return wrapper
