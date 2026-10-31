"""Turning LINQ lambdas into SQLAlchemy expressions.

A lambda is called with the query's *shape* instead of a row: the model class, an alias of it, a column, or a
tuple of them. `lambda h: h.age > 30` called with `Hero` returns the SQL expression `Hero.age > 30`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import and_, case, func, inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.util import AliasedInsp
from sqlalchemy.sql import ClauseElement

from ..core import MISSING, InvalidOperationError

UNTRANSLATABLE = (
    "The LINQ expression could not be translated to SQL. Use & | ~ instead of and/or/not, col(x).in_(...) "
    "instead of `in`, or call as_enumerable() / as_async_enumerable() first to evaluate it in memory"
)


def is_entity(x: Any) -> bool:
    return isinstance(inspect(x, raiseerr=False), Mapper | AliasedInsp)


def is_sql(x: Any) -> bool:
    if isinstance(x, tuple):
        return bool(x) and all(is_sql(i) for i in x)  # pyright: ignore[reportUnknownVariableType]
    return isinstance(x, ClauseElement) or hasattr(x, "__clause_element__") or is_entity(x)


def clause(x: Any) -> Any:
    return x.__clause_element__() if hasattr(x, "__clause_element__") else x


def flat(shape: Any) -> tuple[Any, ...]:
    return shape if isinstance(shape, tuple) else (shape,)


def try_translate(fn: Callable[..., Any], *shape: Any) -> Any:
    """The SQL expression `fn` builds from the shape, or MISSING when it isn't one (client evaluation)."""
    try:
        result = fn(*shape)
    except Exception:  # noqa: BLE001 - any failure to build SQL means: evaluate in memory
        return MISSING
    return result if is_sql(result) else MISSING


def translate(fn: Callable[..., Any], *shape: Any) -> Any:
    result = try_translate(fn, *shape)
    if result is MISSING:
        raise InvalidOperationError(UNTRANSLATABLE)
    return result


def equals(a: Any, b: Any) -> Any:
    """Join condition; composite keys are tuples, compared column by column."""
    if isinstance(a, tuple):
        return and_(*(x == y for x, y in zip(a, b, strict=True)))  # pyright: ignore[reportUnknownArgumentType]
    return a == b


def entity_equals(shape: Any, value: Any) -> Any:
    """Contains(entity): compare primary keys, as EF does."""
    mapper = inspect(shape).mapper
    keys = [mapper.get_property_by_column(c).key for c in mapper.primary_key]
    return and_(*(getattr(shape, k) == getattr(value, k) for k in keys))


class SqlGrouping:
    """What a lambda after group_by receives: `g.key` and SQL aggregates over the group's elements."""

    def __init__(self, key: Any, element: Any) -> None:
        self.key = key
        self._element = element

    def _of(self, selector: Callable[[Any], Any] | None) -> Any:
        return self._element if selector is None else translate(selector, self._element)

    def count(self, predicate: Callable[[Any], Any] | None = None) -> Any:
        return func.count() if predicate is None else func.count(case((translate(predicate, self._element), 1)))

    def long_count(self, predicate: Callable[[Any], Any] | None = None) -> Any:
        return self.count(predicate)

    def any(self, predicate: Callable[[Any], Any] | None = None) -> Any:
        return self.count(predicate) > 0

    def sum(self, selector: Callable[[Any], Any] | None = None) -> Any:
        return func.sum(self._of(selector))

    def min(self, selector: Callable[[Any], Any] | None = None) -> Any:
        return func.min(self._of(selector))

    def max(self, selector: Callable[[Any], Any] | None = None) -> Any:
        return func.max(self._of(selector))

    def average(self, selector: Callable[[Any], Any] | None = None) -> Any:
        return func.avg(self._of(selector))
