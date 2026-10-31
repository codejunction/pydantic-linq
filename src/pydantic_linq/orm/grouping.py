"""GroupedQueryable: IQueryable<IGrouping<K, T>>. select / where / order_by over the groups run as GROUP BY / HAVING."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from ..core import MISSING
from ..core.sorting import Comparer
from ..sync.enumerable import Enumerable
from ..sync.grouping import Grouping
from ..sync.ordered import OrderedEnumerable
from .queryable import Queryable
from .translation import SqlGrouping, clause, flat, translate, try_translate


class GroupedQueryable[K, T](Enumerable[Grouping[K, T]]):
    """Lambdas get `g` with `g.key` and the aggregates `g.count()`, `g.sum(sel)`, `g.min(sel)`, `g.max(sel)`,
    `g.average(sel)`, `g.any()`. The same lambdas work on in-memory Grouping objects, so a select that can't be
    translated (or plain enumeration) groups in memory instead."""

    def __init__(
        self,
        query: Queryable[Any],
        key_selector: Callable[[Any], K],
        element_selector: Callable[[Any], Any] | None,
        having: tuple[Callable[[Any], Any], ...] = (),
        order: tuple[tuple[Callable[[Any], Any], bool, Comparer | None], ...] = (),
    ) -> None:
        self._query = query
        self._key_selector = key_selector
        self._element_selector = element_selector
        self._having = having
        self._group_order = order

    def _copy(self, cls: type[GroupedQueryable[Any, Any]], **changes: Any) -> Any:
        state = {"having": self._having, "order": self._group_order} | changes
        return cls(self._query, self._key_selector, self._element_selector, **state)

    def _in_memory(self, rows: Enumerable[Any]) -> Enumerable[Any]:
        groups: Enumerable[Any] = (
            rows.group_by(self._key_selector)
            if self._element_selector is None
            else rows.group_by(self._key_selector, self._element_selector)
        )
        for predicate in self._having:
            groups = groups.where(predicate)
        for i, (key, descending, comparer) in enumerate(self._group_order):
            ordered: Any = groups
            if i == 0:
                groups = (ordered.order_by_descending if descending else ordered.order_by)(key, comparer)
            else:
                groups = (ordered.then_by_descending if descending else ordered.then_by)(key, comparer)
        return groups

    def __iter__(self) -> Iterator[Grouping[K, T]]:
        return iter(self._in_memory(self._query.as_enumerable()))

    def __repr__(self) -> str:
        return f"GroupedQueryable({self._query!r})"

    def select[R](self, selector: Callable[[Grouping[K, T]], R]) -> Queryable[R]:  # pyright: ignore[reportIncompatibleMethodOverride]
        q = self._query._wrapped()  # pyright: ignore[reportPrivateUsage]
        if q._client is None and all(c is None for *_, c in self._group_order):  # pyright: ignore[reportPrivateUsage]
            shape = q._shape  # pyright: ignore[reportPrivateUsage]
            key = translate(self._key_selector, shape)
            element = shape if self._element_selector is None else translate(self._element_selector, shape)
            g = SqlGrouping(key, element)
            projection = try_translate(selector, g)
            if projection is not MISSING:
                stmt = q._stmt.group_by(*flat(key))  # pyright: ignore[reportPrivateUsage]
                for predicate in self._having:
                    stmt = stmt.having(translate(predicate, g))
                order = tuple((clause(translate(k, g)), d) for k, d, _ in self._group_order)
                stmt = stmt.with_only_columns(*flat(projection))
                return q._with(stmt=stmt, shape=projection, order=order, aggregated=True, includes=())  # pyright: ignore[reportPrivateUsage]
        return q._then(lambda e: self._in_memory(e).select(selector))  # pyright: ignore[reportPrivateUsage]

    def where(self, predicate: Callable[[Grouping[K, T]], Any]) -> GroupedQueryable[K, T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """HAVING."""
        return self._copy(type(self), having=(*self._having, predicate))

    def order_by(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key_selector: Callable[[Grouping[K, T]], Any], comparer: Comparer | None = None
    ) -> OrderedGroupedQueryable[K, T]:
        return self._copy(OrderedGroupedQueryable, order=((key_selector, False, comparer),))

    def order_by_descending(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key_selector: Callable[[Grouping[K, T]], Any], comparer: Comparer | None = None
    ) -> OrderedGroupedQueryable[K, T]:
        return self._copy(OrderedGroupedQueryable, order=((key_selector, True, comparer),))

    def count(self, predicate: Callable[[Grouping[K, T]], Any] | None = None) -> int:
        """The number of groups."""
        source = self if predicate is None else self.where(predicate)
        return source.select(lambda g: g.key).count()

    def long_count(self, predicate: Callable[[Grouping[K, T]], Any] | None = None) -> int:
        return self.count(predicate)

    async def to_list_async(self) -> list[Grouping[K, T]]:
        return self._in_memory(Enumerable(await self._query.to_list_async())).to_list()

    async def count_async(self, predicate: Callable[[Grouping[K, T]], Any] | None = None) -> int:
        source = self if predicate is None else self.where(predicate)
        return await source.select(lambda g: g.key).count_async()


class OrderedGroupedQueryable[K, T](GroupedQueryable[K, T], OrderedEnumerable[Grouping[K, T]]):
    def then_by(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key_selector: Callable[[Grouping[K, T]], Any], comparer: Comparer | None = None
    ) -> OrderedGroupedQueryable[K, T]:
        return self._copy(OrderedGroupedQueryable, order=(*self._group_order, (key_selector, False, comparer)))

    def then_by_descending(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key_selector: Callable[[Grouping[K, T]], Any], comparer: Comparer | None = None
    ) -> OrderedGroupedQueryable[K, T]:
        return self._copy(OrderedGroupedQueryable, order=(*self._group_order, (key_selector, True, comparer)))
