# Entity Framework (SQLModel)

`pydantic_linq.orm` is Entity Framework Core for SQLModel. `DbContext` is the unit of work, and `Queryable` is `IQueryable<T>`: LINQ operators that build one SQL statement and run it when you enumerate the query or call a terminal operator.

```bash
pip install "pydantic-linq[sqlmodel]"
pip install aiosqlite   # or asyncpg, aiomysql, ... for async
```

```python
from sqlmodel import Field, SQLModel, create_engine
from pydantic_linq.orm import DbContext

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    age: int

with DbContext(create_engine("sqlite:///heroes.db")) as db:
    db.ensure_created()
    db.add(Hero(name="Tony", age=48))
    db.save_changes()

    db.set(Hero).where(lambda h: h.age > 30).order_by(lambda h: h.name).select(lambda h: h.name).to_list()
    # SELECT hero.name FROM hero WHERE hero.age > 30 ORDER BY hero.name
```

## How lambdas become SQL

EF Core reads expression trees. Python has none, so a lambda is called once with the query's *shape* instead of a row: the model class, so `lambda h: h.age > 30` returns SQLAlchemy's `Hero.age > 30`. After `select`, the shape is the selected column or tuple of columns. After `join`, it is the pair the result selector built.

That gives three rules:

- Combine conditions with `&`, `|` and `~`. Python's `and`, `or` and `not` can't be overloaded, so `lambda h: h.age > 1 and h.age < 9` can't be translated. Wrap each comparison in parentheses: `(h.age > 1) & (h.age < 9)`.
- Use SQLAlchemy's column methods where Python has syntax: `col(h.name).in_([...])` for `in`, `col(h.team_id).is_(None)` for `is None`, `h.name.contains("x")` / `startswith` / `endswith` for `LIKE`. `col` comes from `sqlmodel`.
- A `where`, `order_by` or join key lambda that can't be translated raises `InvalidOperationError`, as EF Core does. Call `as_enumerable()` first to run the rest of the query in memory.

`to_query_string()` shows the SQL.

## Client evaluation

As in EF Core:

- A `select` whose result isn't SQL (an f-string, a dict, a model, a method call such as `h.name.upper()`) runs in memory on the fetched rows. That is EF's client projection. Every operator after it also runs in memory, with the same lambdas now receiving real objects.
- Every LINQ operator EF can't translate (`zip`, `aggregate`, `chunk`, `take_while`, `skip_last`, `sequence_equal`, ...) is still there. It comes from `Enumerable` and runs over the query's results, as if you had called `AsEnumerable()` first.
- `as_enumerable()` and `as_async_enumerable()` switch to in-memory LINQ explicitly.

## Translated operators

| C# / EF Core | Python | SQL |
|---|---|---|
| `Where` | `where(pred)` | `WHERE` |
| `Select` | `select(sel)` | column list |
| `SelectMany` (over a collection navigation) | `select_many(lambda t: t.heroes[, result])` | `JOIN` |
| `OrderBy` / `OrderByDescending` / `ThenBy` / `ThenByDescending` | same, snake_case | `ORDER BY` |
| `Order` / `OrderDescending` | `order()` / `order_descending()` | `ORDER BY` |
| `Reverse` (after `OrderBy`) | `reverse()` | flips `ORDER BY` |
| `Skip` / `Take` / `Take(Range)` | `skip(n)` / `take(n)` / `take(slice(a, b))` | `OFFSET` / `LIMIT` |
| `Distinct` | `distinct()` | `DISTINCT` |
| `Union` / `Concat` / `Intersect` / `Except` | `union` / `concat` / `intersect` / `except_` | `UNION` / `UNION ALL` / `INTERSECT` / `EXCEPT` |
| `Join` | `join(inner, outer_key, inner_key, result)` | `INNER JOIN` |
| `LeftJoin` / `RightJoin` (EF 10) | `left_join` / `right_join` | `LEFT OUTER JOIN` |
| `GroupBy(...).Select(g => ...)` | `group_by(key[, element]).select(lambda g: ...)` | `GROUP BY` |
| `GroupBy(...).Where(g => g.Count() > 1)` | `.where(lambda g: g.count() > 1)` | `HAVING` |
| `CountBy` | `count_by(key)` | `GROUP BY` + `COUNT` |
| `Count` / `LongCount` / `Any` / `All` / `Contains` | same | `COUNT`, `LIMIT 1`, primary-key compare for entities |
| `First` / `FirstOrDefault` / `Single` / `SingleOrDefault` | same | `LIMIT 1` / `LIMIT 2` |
| `Last` / `LastOrDefault` (after `OrderBy`) | same | reversed `ORDER BY` + `LIMIT 1` |
| `ElementAt` / `ElementAtOrDefault` | same | `OFFSET n LIMIT 1` |
| `Sum` / `Min` / `Max` / `Average` | same | `SUM` / `MIN` / `MAX` / `AVG` |
| `MinBy` / `MaxBy` | `min_by` / `max_by` | `ORDER BY` + `LIMIT 1` |

Inside a group lambda, `g.key` is the key, and `g.count([pred])`, `g.long_count`, `g.any([pred])`, `g.sum(sel)`, `g.min(sel)`, `g.max(sel)` and `g.average(sel)` are SQL aggregates. A composite key is a tuple: `group_by(lambda h: (h.team_id, h.age))`. A group lambda that SQL can't express (for example `lambda g: {g.key: g.count()}`) runs the grouping in memory with the same lambda. Enumerating `group_by(...)` directly also groups in memory and yields `Grouping` objects.

Like LINQ, operators compose in order: `take(3).where(...)` filters the three rows `take` returned (the query is wrapped in a subquery), and `take(5).skip(2)` returns three rows.

`Last`, `LastOrDefault` and `Reverse` need an `order_by` first, and raise `InvalidOperationError` without one, as in EF Core. `Min`, `Max` and `Average` of an empty query raise `InvalidOperationError`; `Sum` returns 0.

## EF Core query features

| EF Core | Python |
|---|---|
| `Include(h => h.Team)` | `include(lambda h: h.team)` |
| `ThenInclude(t => t.Members)` | `then_include(lambda t: t.members)` |
| `AsSplitQuery()` / `AsSingleQuery()` | `as_split_query()` (default: one `SELECT ... IN` per include) / `as_single_query()` (`LEFT OUTER JOIN`s) |
| `AsNoTracking()` / `AsTracking()` | `as_no_tracking()` / `as_tracking()` |
| `TagWith("x")` | `tag_with("x")` (a `/* x */` comment in the SQL) |
| `ToQueryString()` | `to_query_string()` |
| `AsEnumerable()` / `AsAsyncEnumerable()` | `as_enumerable()` / `as_async_enumerable()` |
| `Load()` | `load()` |
| `ExecuteDelete()` | `execute_delete()` → row count |
| `ExecuteUpdate(s => s.SetProperty(h => h.Age, h => h.Age + 1))` | `execute_update(lambda h: {h.age: h.age + 1})` → row count |

`execute_update` and `execute_delete` don't change entities already loaded, as in EF Core. They run inside the session's transaction, so `save_changes()` commits them.

## DbContext

| EF Core | Python |
|---|---|
| `new AppDbContext(options)` | `DbContext(engine)`, `DbContext(session)`, `DbContext(async_engine)` |
| `Set<T>()` / `DbSet<T>` | `db.set(Model)` |
| `Add` / `AddRange` | `add(e)` / `add_range(es)` |
| `Attach` / `Update` / `UpdateRange` | `attach(e)` / `update(e)` / `update_range(es)` |
| `Remove` / `RemoveRange` | `remove(e)` / `remove_range(es)` |
| `Find(key)` | `find(Model, *key)` |
| `SaveChanges()` | `save_changes()` → entities written |
| `ChangeTracker.Clear()` | `clear()` |
| `FromSql($"...")` | `from_sql(Model, "SELECT ... WHERE x > :x", x=1)` |
| `Database.ExecuteSql(...)` | `execute_sql("UPDATE ...", **params)` → row count |
| `Database.BeginTransaction()` | `begin_transaction()` (`commit()` / `rollback()`, or use it in `with`) |
| `Database.EnsureCreated()` / `EnsureDeleted()` | `ensure_created()` / `ensure_deleted()` |
| `using` / `Dispose` | `with DbContext(...)` / `async with DbContext(...)` |

As in EF Core, a query doesn't flush pending changes (the session has autoflush off), and entities keep their values after `save_changes()`. Change tracking itself is SQLAlchemy's: `db.session` is the underlying `Session`.

`from_sql` binds values as `:name` parameters. Don't format values into the SQL string. Operators after `from_sql` compose over it as a subquery.

## Async

Pass an `AsyncEngine` or `AsyncSession`, use `async with`, and await the `*_async` operators. They keep EF's `Async` suffix because the same `Queryable` also has the sync ones.

```python
from sqlalchemy.ext.asyncio import create_async_engine

async with DbContext(create_async_engine("sqlite+aiosqlite:///heroes.db")) as db:
    await db.ensure_created_async()
    db.add(Hero(name="Tony", age=48))
    await db.save_changes_async()
    adults = await db.set(Hero).where(lambda h: h.age >= 18).to_list_async()
```

| Async terminal operators |
|---|
| `to_list_async`, `to_array_async`, `to_hash_set_async`, `to_dictionary_async`, `to_lookup_async` |
| `count_async`, `long_count_async`, `any_async`, `all_async`, `contains_async` |
| `first_async`, `first_or_default_async`, `single_async`, `single_or_default_async`, `last_async`, `last_or_default_async`, `element_at_async`, `element_at_or_default_async` |
| `sum_async`, `min_async`, `max_async`, `average_async`, `min_by_async`, `max_by_async` |
| `for_each_async` (sync or async action), `load_async`, `execute_delete_async`, `execute_update_async` |
| `async for x in query`, `as_async_enumerable()` (every System.Linq.Async operator, in memory) |

On the context: `save_changes_async`, `find_async`, `execute_sql_async`, `begin_transaction_async`, `ensure_created_async`, `ensure_deleted_async`.

A sync terminal operator on an async context, or the other way round, raises `InvalidOperationError`. Lazy loading doesn't work with async sessions, so load relationships with `include`.

## Not ported

- **Migrations.** Use [Alembic](https://alembic.sqlalchemy.org/).
- **Model configuration** (`OnModelCreating`, fluent API, owned types, value converters, global query filters). Configure the SQLModel / SQLAlchemy model instead.
- **Filtered include** (`Include(b => b.Posts.Where(...))`), `GroupJoin` translation, and `Entry(e).State`. `group_join` runs in memory; use `db.session` for the change tracker.
- **Compiled queries.** SQLAlchemy caches compiled statements already.
