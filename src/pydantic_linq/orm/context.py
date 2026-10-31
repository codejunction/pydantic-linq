"""DbContext: EF Core's unit of work over a SQLModel Session or AsyncSession (which already track changes)."""

from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType
from typing import Any, Self

from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import SessionTransaction, aliased
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ..core import InvalidOperationError
from .queryable import Queryable


class DbContext:
    """`with DbContext(engine) as db: db.set(Hero).where(lambda h: h.age > 30).to_list()`.

    Pass an AsyncEngine (or AsyncSession) and use `async with` and the `*_async` methods for async I/O.
    As in EF, queries don't flush pending changes (no autoflush) and entities keep their values after save_changes.
    """

    def __init__(self, bind: Engine | AsyncEngine | Session | AsyncSession) -> None:
        if isinstance(bind, AsyncEngine):
            bind = AsyncSession(bind, expire_on_commit=False, autoflush=False)
        elif isinstance(bind, Engine):
            bind = Session(bind, expire_on_commit=False, autoflush=False)
        self.session = bind

    @property
    def _sync(self) -> Session:
        return self.session.sync_session if isinstance(self.session, AsyncSession) else self.session  # pyright: ignore[reportReturnType]

    def _async(self) -> AsyncSession:
        if not isinstance(self.session, AsyncSession):
            raise InvalidOperationError("The *_async methods need an AsyncEngine or AsyncSession")
        return self.session

    # --- queries ---

    def set[T](self, model: type[T]) -> Queryable[T]:
        """Set<T>() / DbSet<T>: the root query over a table."""
        return Queryable(self.session, model)

    def from_sql[T](self, model: type[T], sql: str, **params: Any) -> Queryable[T]:
        """FromSql: a query over raw SQL that returns the model's columns. Bind values as `:name` params, never
        by formatting them into the string. LINQ operators after it compose over it as a subquery."""
        columns = inspect(model).columns  # pyright: ignore[reportOptionalMemberAccess, reportUnknownMemberType, reportUnknownVariableType]
        sub = text(sql).bindparams(**params).columns(*columns).subquery()  # pyright: ignore[reportUnknownArgumentType]
        alias = aliased(model, sub)
        return Queryable(self.session, model)._with(stmt=select(alias), shape=alias)  # pyright: ignore[reportPrivateUsage]

    def execute_sql(self, sql: str, **params: Any) -> int:
        """Database.ExecuteSql: run a statement; returns the affected row count."""
        return self._sync.execute(text(sql), params).rowcount  # pyright: ignore[reportAttributeAccessIssue, reportDeprecated]

    async def execute_sql_async(self, sql: str, **params: Any) -> int:
        result = await self._async().execute(text(sql), params)  # pyright: ignore[reportDeprecated]
        return result.rowcount  # pyright: ignore[reportAttributeAccessIssue]

    # --- change tracking ---

    def add(self, entity: object) -> None:
        self._sync.add(entity)

    def add_range(self, entities: Iterable[object]) -> None:
        self._sync.add_all(entities)

    def attach(self, entity: object) -> None:
        """Attach: track an entity loaded elsewhere, as unchanged."""
        self._sync.add(entity)

    def update(self, entity: object) -> None:
        """Update: save the detached entity's current values on the next save_changes."""
        self._sync.merge(entity)

    def update_range(self, entities: Iterable[object]) -> None:
        for entity in entities:
            self.update(entity)

    def remove(self, entity: object) -> None:
        self._sync.delete(entity)

    def remove_range(self, entities: Iterable[object]) -> None:
        for entity in entities:
            self._sync.delete(entity)

    def find[T](self, model: type[T], *key: Any) -> T | None:
        """Find: by primary key; returns the tracked entity without a query when it is already loaded."""
        return self._sync.get(model, key[0] if len(key) == 1 else key)

    async def find_async[T](self, model: type[T], *key: Any) -> T | None:
        return await self._async().get(model, key[0] if len(key) == 1 else key)

    def _pending(self) -> int:
        session = self._sync
        return len(session.new) + len(session.dirty) + len(session.deleted)

    def save_changes(self) -> int:
        """SaveChanges: commit; returns the number of entities written."""
        count = self._pending()
        self._sync.commit()
        return count

    async def save_changes_async(self) -> int:
        count = self._pending()
        await self._async().commit()
        return count

    def clear(self) -> None:
        """ChangeTracker.Clear: stop tracking every entity."""
        self._sync.expunge_all()

    # --- database ---

    def begin_transaction(self) -> SessionTransaction:
        """Database.BeginTransaction: call commit() or rollback() on the result, or use it in a `with` block."""
        session = self._sync
        return session.begin_nested() if session.in_transaction() else session.begin()

    async def begin_transaction_async(self) -> Any:
        session = self._async()
        return await (session.begin_nested() if session.in_transaction() else session.begin())

    def ensure_created(self) -> None:
        """Database.EnsureCreated: create the tables of every SQLModel table model that don't exist yet."""
        SQLModel.metadata.create_all(self._sync.get_bind())

    async def ensure_created_async(self) -> None:
        async with self._engine().begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def ensure_deleted(self) -> None:
        """Database.EnsureDeleted: drop the tables of every SQLModel table model."""
        SQLModel.metadata.drop_all(self._sync.get_bind())

    async def ensure_deleted_async(self) -> None:
        async with self._engine().begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    def _engine(self) -> AsyncEngine:
        bind = self._async().bind
        if not isinstance(bind, AsyncEngine):
            raise InvalidOperationError("The AsyncSession must be bound to an AsyncEngine")
        return bind

    # --- lifetime ---

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._sync.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._async().close()
