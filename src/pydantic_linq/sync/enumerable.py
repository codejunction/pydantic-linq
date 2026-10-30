"""Facade of the sync layer: Enumerable = every operator mixin + the pydantic field hook."""

from __future__ import annotations

from typing import Any

from pydantic_core import core_schema

from ..integrations.pydantic import sequence_schema
from .base import EnumerableBase
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


class Enumerable[T](
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
    """IEnumerable<T> with the System.Linq operators. Operators returning sequences are deferred and re-enumerable."""

    __slots__ = ()

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> core_schema.CoreSchema:
        return sequence_schema(cls, source, handler)


EnumerableBase._create = Enumerable
