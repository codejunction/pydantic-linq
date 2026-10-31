"""Queryable: IQueryable<T> over SQLModel, the Entity Framework Core query pipeline.

Operators EF Core translates build one SQL statement. Lambdas receive the query's shape instead of rows (see
translation.py), so `lambda h: h.age > 30` becomes `WHERE hero.age > 30`.

- A where/order_by/join key lambda that can't be translated raises InvalidOperationError, as EF Core does.
- A select whose result isn't SQL (a dict, a model, a function call) runs in memory on the fetched rows, like
  EF's client projection; every later operator then runs in memory too.
- LINQ operators with no SQL form (zip, aggregate, chunk, take_while, ...) come from Enumerable and run in
  memory over the results, as if as_enumerable() were called first.

Every terminal operator has an awaitable `*_async` twin (EF's ToListAsync, FirstAsync, ...) for an AsyncSession.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Generator, Iterable, Iterator
from typing import TYPE_CHECKING, Any, cast, overload

from sqlalchemy import (
    Select,
    delete,
    except_,
    func,
    inspect,
    intersect,
    select,
    union,
    union_all,
    update,
)
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    InstanceState,
    RelationshipProperty,
    Session,
    aliased,
    joinedload,
    selectinload,
)
from sqlalchemy.sql import Executable

from ..aio.base import call
from ..aio.enumerable import AsyncEnumerable
from ..core import MISSING, InvalidOperationError
from ..core.errors import MORE_THAN_ONE, MORE_THAN_ONE_MATCH, NO_ELEMENTS, NO_MATCH
from ..core.sorting import Comparer
from ..sync.enumerable import Enumerable
from ..sync.grouping import Lookup
from ..sync.ordered import OrderedEnumerable
from .translation import (
    UNTRANSLATABLE,
    clause,
    entity_equals,
    equals,
    flat,
    is_entity,
    translate,
    try_translate,
)

if TYPE_CHECKING:
    from .grouping import GroupedQueryable

type AnySession = Session | AsyncSession
type Request = tuple[str, Any]
"""What a plan asks the driver to run: ("rows", Queryable), ("scalar", statement) or ("rowcount", statement)."""
type Plan[R] = Generator[Request, Any, R]
type ClientOp = Callable[[Any], Any]

NO_ORDER = "Queries performing '{}' must have a deterministic sort order: call order_by first"


class Queryable[T](Enumerable[T]):
    """A query against the database. Nothing runs until iteration or a terminal operator."""

    def __init__(self, session: AnySession, model: type[T]) -> None:
        self._session = session
        self._stmt: Select[Any] = select(model)  # FROM / WHERE / columns; order and paging are applied last
        self._shape: Any = model
        self._skip = 0
        self._take: int | None = None
        self._order: tuple[tuple[Any, bool], ...] = ()
        self._client: ClientOp | None = None  # in-memory operators applied to the fetched rows
        self._includes: tuple[tuple[Callable[[Any], Any], ...], ...] = ()
        self._loader: Callable[..., Any] = selectinload
        self._tracking = True
        self._aggregated = False  # after a group_by select: filtering must wrap it, not add to it
        self._tags: tuple[str, ...] = ()

    # --- plumbing ---

    def _with(self, cls: type[Queryable[Any]] | None = None, **changes: Any) -> Any:
        cls = cls or Queryable
        q = cls.__new__(cls)
        q.__dict__.update(self.__dict__)
        for name, value in changes.items():
            setattr(q, f"_{name}", value)
        return q

    def _then(self, op: ClientOp, cls: type[Queryable[Any]] | None = None) -> Any:
        prev = self._client
        return self._with(cls, client=op if prev is None else lambda e: op(prev(e)))

    def _statement(self) -> Select[Any]:
        stmt = self._stmt
        if self._includes and is_entity(self._shape):
            stmt = stmt.options(*map(self._loader_option, self._includes))
        if self._tags:
            stmt = stmt.prefix_with(" ".join(f"/* {t} */" for t in self._tags))
        if self._order:
            stmt = stmt.order_by(*(e.desc() if descending else e for e, descending in self._order))
        if self._skip:
            stmt = stmt.offset(self._skip)
        return stmt if self._take is None else stmt.limit(self._take)

    def _loader_option(self, chain: tuple[Callable[[Any], Any], ...]) -> Any:
        option, target = None, self._shape
        for navigation in chain:
            attr = translate(navigation, target)
            option = self._loader(attr) if option is None else getattr(option, self._loader.__name__)(attr)
            target = attr.property.mapper.class_
        return option

    def _from_subquery(self, sub: Any) -> Any:
        """A query over `sub`'s rows, with the same shape."""
        reset = {"skip": 0, "take": None, "order": (), "aggregated": False}
        if is_entity(self._shape):
            alias = aliased(inspect(self._shape).mapper.class_, sub)
            return self._with(stmt=select(alias), shape=alias, **reset)
        if isinstance(self._shape, tuple) and any(map(is_entity, self._shape)):  # pyright: ignore[reportUnknownArgumentType]
            raise InvalidOperationError(UNTRANSLATABLE)
        columns = tuple(sub.c)
        shape = columns if isinstance(self._shape, tuple) else columns[0]
        return self._with(stmt=select(*columns), shape=shape, **reset)

    def _wrapped(self) -> Queryable[T]:
        """Filtering or sorting after skip/take (or after aggregation) applies to those rows: wrap them in a subquery."""
        if not self._skip and self._take is None and not self._aggregated:
            return self
        sub = self._statement().subquery()
        q = self._from_subquery(sub)
        q._order = tuple((c, d) for e, d in self._order if (c := sub.corresponding_column(clause(e))) is not None)
        return q

    def _sync_session(self) -> Session:
        return self._session.sync_session if isinstance(self._session, AsyncSession) else self._session

    def _materialize(self, q: Queryable[Any], result: Any) -> list[Any]:
        if q._loader is joinedload:
            result = result.unique()
        single = len(q._stmt.column_descriptions) == 1
        rows = list(result.scalars() if single else map(tuple, result))
        if not q._tracking:
            session = self._sync_session()
            for value in (v for row in rows for v in (row if isinstance(row, tuple) else (row,))):
                if isinstance(inspect(value, raiseerr=False), InstanceState) and value in session:
                    session.expunge(value)
        return rows if q._client is None else list(q._client(Enumerable(rows)))

    def _result(self, request: Request, result: Any) -> Any:
        kind, payload = request
        if kind == "rows":
            return self._materialize(payload, result)
        return result.scalar() if kind == "scalar" else result.rowcount

    @staticmethod
    def _executable(request: Request) -> Executable:
        kind, payload = request
        return payload._statement() if kind == "rows" else payload

    def _drive[R](self, plan: Plan[R]) -> R:
        if isinstance(self._session, AsyncSession):
            raise InvalidOperationError("This query uses an AsyncSession: call the *_async operator")
        session = self._session
        run = getattr(session, "exec", session.execute)  # sqlmodel.Session marks execute() deprecated
        try:
            request = next(plan)
            while True:
                request = plan.send(self._result(request, run(self._executable(request))))
        except StopIteration as stop:
            return stop.value

    async def _drive_async[R](self, plan: Plan[R]) -> R:
        if not isinstance(self._session, AsyncSession):
            raise InvalidOperationError("The *_async operators need an AsyncSession")
        session = self._session
        run = getattr(session, "exec", session.execute)
        try:
            request = next(plan)
            while True:
                request = plan.send(self._result(request, await run(self._executable(request))))
        except StopIteration as stop:
            return stop.value

    def _plan(self, name: str, args: tuple[Any, ...]) -> Plan[Any]:
        return self._client_plan(name, args) if self._client else getattr(self, f"_plan_{name}")(*args)

    def _client_plan(self, name: str, args: tuple[Any, ...]) -> Plan[Any]:
        rows = yield ("rows", self)
        return getattr(Enumerable(rows), name)(*args)

    def _go(self, name: str, *args: Any) -> Any:
        return self._drive(self._plan(name, args))

    async def _go_async(self, name: str, *args: Any) -> Any:
        return await self._drive_async(self._plan(name, args))

    def try_get_non_enumerated_count(self) -> int | None:
        return None

    def to_query_string(self) -> str:
        """ToQueryString: the SQL this query runs."""
        stmt = self._statement()
        try:
            return str(stmt.compile(compile_kwargs={"literal_binds": True}))
        except (CompileError, NotImplementedError):  # a bound value with no literal form
            return str(stmt)

    def __repr__(self) -> str:
        return f"Queryable({self.to_query_string()!r})"

    # --- EF query options ---

    def include(self, navigation: Callable[[T], Any]) -> Queryable[T]:
        """Include: eager-load a relationship (`lambda h: h.team`)."""
        return self._with(type(self), includes=(*self._includes, (navigation,)))

    def then_include(self, navigation: Callable[[Any], Any]) -> Queryable[T]:
        """ThenInclude: eager-load a relationship of the entity the previous include loaded."""
        if not self._includes:
            raise InvalidOperationError("then_include must follow include")
        return self._with(type(self), includes=(*self._includes[:-1], (*self._includes[-1], navigation)))

    def as_no_tracking(self) -> Queryable[T]:
        """AsNoTracking: returned entities are detached, so changes to them aren't saved."""
        return self._with(type(self), tracking=False)

    def as_tracking(self) -> Queryable[T]:
        return self._with(type(self), tracking=True)

    def as_split_query(self) -> Queryable[T]:
        """AsSplitQuery: each include loads in its own SELECT ... IN query (the default here)."""
        return self._with(type(self), loader=selectinload)

    def as_single_query(self) -> Queryable[T]:
        """AsSingleQuery: includes load through LEFT OUTER JOINs in the main query."""
        return self._with(type(self), loader=joinedload)

    def tag_with(self, tag: str) -> Queryable[T]:
        """TagWith: put a comment into the SQL, to find the query in logs."""
        return self._with(type(self), tags=(*self._tags, tag.replace("*/", "* /")))

    def as_enumerable(self) -> Enumerable[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """AsEnumerable: later operators run in memory. The query runs on each enumeration."""
        return Enumerable(self)

    def as_async_enumerable(self) -> AsyncEnumerable[T]:
        """AsAsyncEnumerable: continue with the System.Linq.Async operators over the results."""
        return AsyncEnumerable(self)

    def to_async_enumerable(self) -> AsyncEnumerable[T]:
        return self.as_async_enumerable()

    # --- filtering, projection ---

    def where(self, predicate: Callable[[T], Any]) -> Queryable[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self._client:
            return self._then(lambda e: e.where(predicate))
        q = self._wrapped()
        return q._with(stmt=q._stmt.where(translate(predicate, q._shape)))

    def select[U](self, selector: Callable[[T], U]) -> Queryable[U]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Columns (`lambda h: h.name`, `lambda h: (h.id, h.name)`) are selected in SQL; anything else runs in memory."""
        shape = MISSING if self._client else try_translate(selector, self._shape)
        if shape is MISSING:
            return self._then(lambda e: e.select(selector))
        return self._with(stmt=self._stmt.with_only_columns(*flat(shape)), shape=shape, includes=())

    @overload
    def select_many[U](self, selector: Callable[[T], Iterable[U]]) -> Queryable[U]: ...
    @overload
    def select_many[C, U](
        self, selector: Callable[[T], Iterable[C]], result_selector: Callable[[T, C], U]
    ) -> Queryable[U]: ...
    def select_many(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, selector: Callable[[T], Iterable[Any]], result_selector: Callable[[T, Any], Any] | None = None
    ) -> Queryable[Any]:
        """SelectMany over a collection navigation (`lambda t: t.heroes`) is a JOIN; anything else runs in memory."""
        q = self._wrapped()
        attr = MISSING if self._client else try_translate(selector, q._shape)
        if attr is MISSING or not isinstance(getattr(attr, "property", None), RelationshipProperty):
            if result_selector is None:
                return self._then(lambda e: e.select_many(selector))
            return self._then(lambda e: e.select_many(selector, result_selector))
        alias = aliased(attr.property.mapper.class_)
        joined = q._with(stmt=q._stmt.join(attr.of_type(alias)), includes=())
        if result_selector is None:
            return joined._with(stmt=joined._stmt.with_only_columns(alias), shape=alias)
        pair = joined._with(stmt=joined._stmt.with_only_columns(*flat(q._shape), alias), shape=(q._shape, alias))
        return pair.select(lambda p: result_selector(*p))  # pyright: ignore[reportUnknownLambdaType]

    def distinct(self) -> Queryable[T]:
        if self._client:
            return self._then(lambda e: e.distinct())
        q = self._wrapped()
        return q._with(stmt=q._stmt.distinct())

    # --- sorting ---

    def _ordered(self, key_selector: Callable[[T], Any], comparer: Comparer | None, descending: bool) -> Any:
        if self._client or comparer is not None:
            op = "order_by_descending" if descending else "order_by"
            return self._then(lambda e: getattr(e, op)(key_selector, comparer), OrderedQueryable)
        q = self._wrapped()
        return q._with(OrderedQueryable, order=((clause(translate(key_selector, q._shape)), descending),))

    def order_by(self, key_selector: Callable[[T], Any], comparer: Comparer | None = None) -> OrderedQueryable[T]:
        return self._ordered(key_selector, comparer, False)

    def order_by_descending(
        self, key_selector: Callable[[T], Any], comparer: Comparer | None = None
    ) -> OrderedQueryable[T]:
        return self._ordered(key_selector, comparer, True)

    def order(self, comparer: Comparer | None = None) -> OrderedQueryable[T]:
        return self.order_by(lambda x: x, comparer)

    def order_descending(self, comparer: Comparer | None = None) -> OrderedQueryable[T]:
        return self.order_by_descending(lambda x: x, comparer)

    def reverse(self) -> Queryable[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self._client:
            return self._then(lambda e: e.reverse())
        q = self._wrapped()
        if not q._order:
            raise InvalidOperationError(NO_ORDER.format("reverse"))
        return q._with(order=tuple((e, not d) for e, d in q._order))

    # --- partitioning ---

    def skip(self, count: int) -> Queryable[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self._client:
            return self._then(lambda e: e.skip(count))
        count = max(count, 0)
        take = None if self._take is None else max(self._take - count, 0)
        return self._with(skip=self._skip + count, take=take)

    def take(self, count: int | slice) -> Queryable[T]:
        """Take(int) or Take(Range); a range with negative bounds or a step runs in memory."""
        if isinstance(count, slice):
            s = count
            if self._client or s.step is not None or any(b is not None and b < 0 for b in (s.start, s.stop)):
                return self._then(lambda e: e.take(s))
            start = s.start or 0
            skipped = self.skip(start)
            return skipped if s.stop is None else skipped.take(max(s.stop - start, 0))
        if self._client:
            return self._then(lambda e: e.take(count))
        count = max(count, 0)
        return self._with(take=count if self._take is None else min(self._take, count))

    # --- sets ---

    def _set_operation(self, second: Iterable[T], sql: Callable[..., Any], name: str) -> Queryable[T]:
        if isinstance(second, Queryable) and not (self._client or second._client):
            members = (select(*q._statement().subquery().c) for q in (self, cast(Queryable[T], second)))
            return self._from_subquery(sql(*members).subquery())
        return self._then(lambda e: getattr(e, name)(second))

    def concat(self, second: Iterable[T]) -> Queryable[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._set_operation(second, union_all, "concat")

    def union(self, second: Iterable[T]) -> Queryable[T]:
        return self._set_operation(second, union, "union")

    def intersect(self, second: Iterable[T]) -> Queryable[T]:
        return self._set_operation(second, intersect, "intersect")

    def except_(self, second: Iterable[T]) -> Queryable[T]:
        return self._set_operation(second, except_, "except_")

    # --- joins ---

    def _join(
        self,
        inner: Iterable[Any],
        outer_key_selector: Callable[..., Any],
        inner_key_selector: Callable[..., Any],
        result_selector: Callable[..., Any],
        name: str,
        outer: bool,
    ) -> Any:
        if not isinstance(inner, Queryable) or self._client or inner._client:
            keys = (outer_key_selector, inner_key_selector)
            return self._then(lambda e: getattr(e, name)(inner, *keys, result_selector))
        q, sub = self._wrapped(), cast(Queryable[Any], inner)._statement().subquery()
        right = cast(Queryable[Any], inner)._from_subquery(sub)
        target = right._shape if is_entity(right._shape) else sub
        on = equals(translate(outer_key_selector, q._shape), translate(inner_key_selector, right._shape))
        stmt = q._stmt.join(target, on, isouter=outer).with_only_columns(*flat(q._shape), *flat(right._shape))
        pair = q._with(stmt=stmt, shape=(q._shape, right._shape), includes=())
        return pair.select(lambda p: result_selector(*p))  # pyright: ignore[reportUnknownLambdaType]

    def join[I, K, R](  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T, I], R],
    ) -> Queryable[R]:
        """Join with another Queryable is an INNER JOIN."""
        return self._join(inner, outer_key_selector, inner_key_selector, result_selector, "join", False)

    def left_join[I, K, R](  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T, I | None], R],
    ) -> Queryable[R]:
        """LeftJoin (.NET 10 / EF 10): LEFT OUTER JOIN; unmatched rows pair with None."""
        return self._join(inner, outer_key_selector, inner_key_selector, result_selector, "left_join", True)

    def right_join[I, K, R](  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        inner: Iterable[I],
        outer_key_selector: Callable[[T], K],
        inner_key_selector: Callable[[I], K],
        result_selector: Callable[[T | None, I], R],
    ) -> Queryable[R]:
        """RightJoin (.NET 10 / EF 10): run as the inner query LEFT JOIN this one."""
        if isinstance(inner, Queryable) and not (self._client or inner._client):
            return cast(Queryable[I], inner).left_join(
                self, inner_key_selector, outer_key_selector, lambda i, o: result_selector(o, i)
            )
        return self._then(lambda e: e.right_join(inner, outer_key_selector, inner_key_selector, result_selector))

    # --- grouping ---

    @overload
    def group_by[K](self, key_selector: Callable[[T], K]) -> GroupedQueryable[K, T]: ...
    @overload
    def group_by[K, E](
        self, key_selector: Callable[[T], K], element_selector: Callable[[T], E]
    ) -> GroupedQueryable[K, E]: ...
    @overload
    def group_by[K, R](
        self, key_selector: Callable[[T], K], *, result_selector: Callable[[K, Enumerable[T]], R]
    ) -> Queryable[R]: ...
    @overload
    def group_by[K, E, R](
        self,
        key_selector: Callable[[T], K],
        element_selector: Callable[[T], E],
        *,
        result_selector: Callable[[K, Enumerable[E]], R],
    ) -> Queryable[R]: ...
    def group_by(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        key_selector: Callable[[T], Any],
        element_selector: Callable[[T], Any] | None = None,
        *,
        result_selector: Callable[[Any, Enumerable[Any]], Any] | None = None,
    ) -> Any:
        """GroupBy. Followed by select / where / order_by over `g.key`, `g.count()`, `g.sum(...)`, ... it runs as
        GROUP BY / HAVING. Enumerated directly, the groups are built in memory."""
        from .grouping import GroupedQueryable

        groups = GroupedQueryable(self, key_selector, element_selector)
        return groups if result_selector is None else groups.select(lambda g: result_selector(g.key, g))  # pyright: ignore[reportArgumentType]

    def count_by[K](self, key_selector: Callable[[T], K]) -> Queryable[tuple[K, int]]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.group_by(key_selector).select(lambda g: (g.key, g.count()))

    # --- terminal operators: each _plan_* yields the statements it needs and returns the result ---

    def _where_or_self(self, predicate: Callable[[T], Any] | None) -> Queryable[T]:
        return self if predicate is None else self.where(predicate)

    @staticmethod
    def _found(rows: list[Any], default: Any, missing: str) -> Any:
        if rows:
            return rows[0]
        if default is MISSING:
            raise InvalidOperationError(missing)
        return default

    def _plan_to_list(self) -> Plan[list[T]]:
        return (yield ("rows", self))

    def _plan_count(self, predicate: Callable[[T], Any] | None) -> Plan[int]:
        sub = self._where_or_self(predicate)._statement().subquery()
        return (yield ("scalar", select(func.count()).select_from(sub)))

    def _plan_any(self, predicate: Callable[[T], Any] | None) -> Plan[bool]:
        return bool((yield ("rows", self._where_or_self(predicate).take(1))))

    def _plan_all(self, predicate: Callable[[T], Any]) -> Plan[bool]:
        return not (yield from self._plan_any(lambda s: ~translate(predicate, s)))

    def _plan_contains(self, value: T) -> Plan[bool]:
        return (yield from self._plan_any(lambda s: entity_equals(s, value) if is_entity(s) else equals(s, value)))

    def _plan_first(self, predicate: Callable[[T], Any] | None, default: Any = MISSING) -> Plan[Any]:
        rows = yield ("rows", self._where_or_self(predicate).take(1))
        return self._found(rows, default, NO_ELEMENTS if predicate is None else NO_MATCH)

    def _plan_single(self, predicate: Callable[[T], Any] | None, default: Any = MISSING) -> Plan[Any]:
        rows = yield ("rows", self._where_or_self(predicate).take(2))
        if len(rows) > 1:
            raise InvalidOperationError(MORE_THAN_ONE if predicate is None else MORE_THAN_ONE_MATCH)
        return self._found(rows, default, NO_ELEMENTS if predicate is None else NO_MATCH)

    def _plan_last(self, predicate: Callable[[T], Any] | None, default: Any = MISSING) -> Plan[Any]:
        q = self._where_or_self(predicate)._wrapped()
        if not q._order:
            raise InvalidOperationError(NO_ORDER.format("last"))
        rows = yield ("rows", q.reverse().take(1))
        return self._found(rows, default, NO_ELEMENTS if predicate is None else NO_MATCH)

    def _plan_element_at(self, index: int, default: Any = MISSING) -> Plan[Any]:
        if index < 0:  # ElementAt(^n) needs the row count: run it in memory
            rows = yield ("rows", self)
            return Enumerable(rows).element_at(index) if default is MISSING else Enumerable(rows).element_at_or_default(index, default)
        rows = yield ("rows", self.skip(index).take(1))
        if not rows and default is MISSING:
            raise IndexError("Index was out of range")
        return rows[0] if rows else default

    def _plan_aggregate(self, fn: Any, selector: Callable[[T], Any] | None, name: str) -> Plan[Any]:
        source = self if selector is None else self.select(selector)
        if source._client or is_entity(source._shape):
            rows = yield ("rows", source)
            return getattr(Enumerable(rows), name)()
        sub = source._statement().subquery()
        result = yield ("scalar", select(fn(*sub.c)).select_from(sub))
        if result is None and name != "sum":
            raise InvalidOperationError(NO_ELEMENTS)
        return 0 if result is None else result

    def _plan_sum(self, selector: Callable[[T], Any] | None) -> Plan[Any]:
        return (yield from self._plan_aggregate(func.sum, selector, "sum"))

    def _plan_min(self, selector: Callable[[T], Any] | None) -> Plan[Any]:
        return (yield from self._plan_aggregate(func.min, selector, "min"))

    def _plan_max(self, selector: Callable[[T], Any] | None) -> Plan[Any]:
        return (yield from self._plan_aggregate(func.max, selector, "max"))

    def _plan_average(self, selector: Callable[[T], Any] | None) -> Plan[float]:
        return float((yield from self._plan_aggregate(func.avg, selector, "average")))

    def _plan_min_by(self, key_selector: Callable[[T], Any]) -> Plan[T]:
        return (yield from self.order_by(key_selector)._plan_first(None))

    def _plan_max_by(self, key_selector: Callable[[T], Any]) -> Plan[T]:
        return (yield from self.order_by_descending(key_selector)._plan_first(None))

    def _bulk_target(self) -> tuple[Any, Any]:
        """The table an ExecuteUpdate / ExecuteDelete writes to, and the WHERE that picks its rows."""
        if self._client or self._aggregated or not is_entity(self._shape):
            raise InvalidOperationError("execute_update / execute_delete need an unprojected query over one entity")
        mapper = inspect(self._shape).mapper
        model = mapper.class_
        if self._shape is model and not (self._skip or self._take is not None):
            return model, self._stmt.whereclause
        if len(mapper.primary_key) != 1:
            raise InvalidOperationError("execute_update / execute_delete after paging need a single-column key")
        key = mapper.primary_key[0]
        ids = self.select(lambda s: getattr(s, mapper.get_property_by_column(key).key))._statement()
        return model, key.in_(ids)

    def _plan_execute_delete(self) -> Plan[int]:
        model, where = self._bulk_target()
        stmt = delete(model) if where is None else delete(model).where(where)
        return (yield ("rowcount", stmt.execution_options(synchronize_session=False)))

    def _plan_execute_update(self, setters: Callable[[T], dict[Any, Any]]) -> Plan[int]:
        model, where = self._bulk_target()
        stmt = update(model) if where is None else update(model).where(where)
        values = setters(cast(T, model))
        return (yield ("rowcount", stmt.values(values).execution_options(synchronize_session=False)))

    def _plan_load(self) -> Plan[None]:
        yield ("rows", self)

    # --- sync terminal operators ---

    def __iter__(self) -> Iterator[T]:
        return iter(self._go("to_list"))

    def to_list(self) -> list[T]:
        return self._go("to_list")

    def count(self, predicate: Callable[[T], Any] | None = None) -> int:
        return self._go("count", predicate)

    def long_count(self, predicate: Callable[[T], Any] | None = None) -> int:
        return self._go("count", predicate)

    def any(self, predicate: Callable[[T], Any] | None = None) -> bool:
        return self._go("any", predicate)

    def all(self, predicate: Callable[[T], Any]) -> bool:
        return self._go("all", predicate)

    def contains(self, value: T) -> bool:
        return self._go("contains", value)

    def first(self, predicate: Callable[[T], Any] | None = None) -> T:
        return self._go("first", predicate)

    def first_or_default(self, predicate: Callable[[T], Any] | None = None, default: T | None = None) -> T | None:
        return self._go("first", predicate, default)

    def single(self, predicate: Callable[[T], Any] | None = None) -> T:
        return self._go("single", predicate)

    def single_or_default(self, predicate: Callable[[T], Any] | None = None, default: T | None = None) -> T | None:
        return self._go("single", predicate, default)

    def last(self, predicate: Callable[[T], Any] | None = None) -> T:
        return self._go("last", predicate)

    def last_or_default(self, predicate: Callable[[T], Any] | None = None, default: T | None = None) -> T | None:
        return self._go("last", predicate, default)

    def element_at(self, index: int) -> T:
        return self._go("element_at", index)

    def element_at_or_default(self, index: int, default: T | None = None) -> T | None:
        return self._go("element_at", index, default)

    def sum(self, selector: Callable[[T], Any] | None = None) -> Any:
        return self._go("sum", selector)

    def min(self, selector: Callable[[T], Any] | None = None) -> Any:
        return self._go("min", selector)

    def max(self, selector: Callable[[T], Any] | None = None) -> Any:
        return self._go("max", selector)

    def average(self, selector: Callable[[T], Any] | None = None) -> float:
        return self._go("average", selector)

    def min_by(self, key_selector: Callable[[T], Any]) -> T:
        return self._go("min_by", key_selector)

    def max_by(self, key_selector: Callable[[T], Any]) -> T:
        return self._go("max_by", key_selector)

    def load(self) -> None:
        """Load: run the query so its entities are tracked, without returning them."""
        self._go("load")

    def execute_delete(self) -> int:
        """ExecuteDelete: one DELETE for the matching rows; returns the row count. Tracked entities aren't
        updated. The statement runs in the session's transaction, so save_changes() commits it."""
        return self._go("execute_delete")

    def execute_update(self, setters: Callable[[T], dict[Any, Any]]) -> int:
        """ExecuteUpdate: `execute_update(lambda h: {h.age: h.age + 1})` is one UPDATE; returns the row count."""
        return self._go("execute_update", setters)

    # --- async terminal operators (EF's *Async methods) ---

    async def __aiter__(self) -> AsyncIterator[T]:
        for x in await self.to_list_async():
            yield x

    async def to_list_async(self) -> list[T]:
        return await self._go_async("to_list")

    async def to_array_async(self) -> list[T]:
        return await self.to_list_async()

    async def to_hash_set_async(self) -> set[T]:
        return set(await self.to_list_async())

    async def to_dictionary_async[K](
        self, key_selector: Callable[[T], K], element_selector: Callable[[T], Any] | None = None
    ) -> dict[K, Any]:
        rows = Enumerable(await self.to_list_async())
        if element_selector is None:
            return rows.to_dictionary(key_selector)
        return rows.to_dictionary(key_selector, element_selector)

    async def to_lookup_async[K](self, key_selector: Callable[[T], K]) -> Lookup[K, T]:
        return Enumerable(await self.to_list_async()).to_lookup(key_selector)

    async def count_async(self, predicate: Callable[[T], Any] | None = None) -> int:
        return await self._go_async("count", predicate)

    async def long_count_async(self, predicate: Callable[[T], Any] | None = None) -> int:
        return await self._go_async("count", predicate)

    async def any_async(self, predicate: Callable[[T], Any] | None = None) -> bool:
        return await self._go_async("any", predicate)

    async def all_async(self, predicate: Callable[[T], Any]) -> bool:
        return await self._go_async("all", predicate)

    async def contains_async(self, value: T) -> bool:
        return await self._go_async("contains", value)

    async def first_async(self, predicate: Callable[[T], Any] | None = None) -> T:
        return await self._go_async("first", predicate)

    async def first_or_default_async(
        self, predicate: Callable[[T], Any] | None = None, default: T | None = None
    ) -> T | None:
        return await self._go_async("first", predicate, default)

    async def single_async(self, predicate: Callable[[T], Any] | None = None) -> T:
        return await self._go_async("single", predicate)

    async def single_or_default_async(
        self, predicate: Callable[[T], Any] | None = None, default: T | None = None
    ) -> T | None:
        return await self._go_async("single", predicate, default)

    async def last_async(self, predicate: Callable[[T], Any] | None = None) -> T:
        return await self._go_async("last", predicate)

    async def last_or_default_async(
        self, predicate: Callable[[T], Any] | None = None, default: T | None = None
    ) -> T | None:
        return await self._go_async("last", predicate, default)

    async def element_at_async(self, index: int) -> T:
        return await self._go_async("element_at", index)

    async def element_at_or_default_async(self, index: int, default: T | None = None) -> T | None:
        return await self._go_async("element_at", index, default)

    async def sum_async(self, selector: Callable[[T], Any] | None = None) -> Any:
        return await self._go_async("sum", selector)

    async def min_async(self, selector: Callable[[T], Any] | None = None) -> Any:
        return await self._go_async("min", selector)

    async def max_async(self, selector: Callable[[T], Any] | None = None) -> Any:
        return await self._go_async("max", selector)

    async def average_async(self, selector: Callable[[T], Any] | None = None) -> float:
        return await self._go_async("average", selector)

    async def min_by_async(self, key_selector: Callable[[T], Any]) -> T:
        return await self._go_async("min_by", key_selector)

    async def max_by_async(self, key_selector: Callable[[T], Any]) -> T:
        return await self._go_async("max_by", key_selector)

    async def for_each_async(self, action: Callable[[T], Any]) -> None:
        """ForEachAsync: `action` may be sync or async."""
        for x in await self.to_list_async():
            await call(action, x)

    async def load_async(self) -> None:
        await self._go_async("load")

    async def execute_delete_async(self) -> int:
        return await self._go_async("execute_delete")

    async def execute_update_async(self, setters: Callable[[T], dict[Any, Any]]) -> int:
        return await self._go_async("execute_update", setters)


class OrderedQueryable[T](Queryable[T], OrderedEnumerable[T]):
    """IOrderedQueryable<T>: then_by / then_by_descending add ORDER BY columns."""

    def _then_ordered(self, key_selector: Callable[[T], Any], comparer: Comparer | None, descending: bool) -> Any:
        if self._client or comparer is not None:
            op = "then_by_descending" if descending else "then_by"
            return self._then(lambda e: getattr(e, op)(key_selector, comparer), OrderedQueryable)
        key = clause(translate(key_selector, self._shape))
        return self._with(OrderedQueryable, order=(*self._order, (key, descending)))

    def then_by(self, key_selector: Callable[[T], Any], comparer: Comparer | None = None) -> OrderedQueryable[T]:
        return self._then_ordered(key_selector, comparer, False)

    def then_by_descending(
        self, key_selector: Callable[[T], Any], comparer: Comparer | None = None
    ) -> OrderedQueryable[T]:
        return self._then_ordered(key_selector, comparer, True)
