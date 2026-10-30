"""Facade of the async layer: AsyncEnumerable = every async operator mixin."""

from __future__ import annotations

from .base import AsyncEnumerableBase
from .operators import (
    Aggregation,
    Concatenation,
    Conversion,
    Element,
    Equality,
    Filtering,
    Generation,
    GroupingOps,
    Joining,
    Partitioning,
    Projection,
    Quantifiers,
    Sets,
    Sorting,
)


class AsyncEnumerable[T](
    Generation[T],
    Filtering[T],
    Projection[T],
    Partitioning[T],
    Concatenation[T],
    Sets[T],
    Sorting[T],
    GroupingOps[T],
    Joining[T],
    Element[T],
    Quantifiers[T],
    Equality[T],
    Aggregation[T],
    Conversion[T],
):
    """IAsyncEnumerable<T> with the System.Linq.Async operators.

    Wraps any sync or async iterable. Sequence operators are deferred; terminal operators are awaitable.
    Selectors may be plain functions or ``async def``.
    """

    __slots__ = ()


AsyncEnumerableBase._create = AsyncEnumerable
