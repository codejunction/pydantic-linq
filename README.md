# pydantic-linq

[![PyPI](https://img.shields.io/pypi/v/pydantic-linq)](https://pypi.org/project/pydantic-linq/)
[![Python](https://img.shields.io/pypi/pyversions/pydantic-linq)](https://pypi.org/project/pydantic-linq/)
[![CI](https://github.com/codejunction/pydantic-linq/actions/workflows/ci.yml/badge.svg)](https://github.com/codejunction/pydantic-linq/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-github%20pages-blue)](https://codejunction.github.io/pydantic-linq/)

C# LINQ for Python. It has every `System.Linq` and `System.Linq.Async` operator, is fully typed, and works with Pydantic models.

**Documentation:** https://codejunction.github.io/pydantic-linq/

```bash
pip install pydantic-linq
```

```python
from pydantic import BaseModel
from pydantic_linq import Enumerable

class Row(BaseModel):
    id: int
    tag: str

rows = Enumerable([Row(id=1, tag="a"), Row(id=2, tag="b"), Row(id=3, tag="a")])

rows.where(lambda r: r.tag == "a").select(lambda r: r.id).to_list()            # [1, 3]
rows.group_by(lambda r: r.tag).select(lambda g: (g.key, g.count())).to_list()  # [('a', 2), ('b', 1)]
rows.order_by_descending(lambda r: r.id).then_by(lambda r: r.tag).first()
```

## Async

`AsyncEnumerable` covers System.Linq.Async. It wraps any sync or async iterable. Sequence operators are deferred, and terminal operators are awaited:

```python
from pydantic_linq import AsyncEnumerable

async def load_age(r: Row) -> int: ...

ages = await AsyncEnumerable(rows).where(lambda r: r.id > 1).select(load_age).to_list()
```

A selector or predicate can be a plain function or an `async def`, so there are no separate `*Await` overloads. Terminal operators keep the sync names (`to_list`, `first`, `count`) and are awaited. The C# `Async` suffix is dropped.

## Entity Framework (SQLModel)

`pydantic_linq.orm` is Entity Framework Core for SQLModel. The same LINQ operators build SQL, and the EF features are there: `DbContext`, `include` / `then_include`, `as_no_tracking`, `execute_update` / `execute_delete`, `from_sql`, and a `*_async` twin of every terminal operator.

```bash
pip install "pydantic-linq[sqlmodel]"
```

```python
from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from pydantic_linq.orm import DbContext

with DbContext(create_engine("sqlite:///app.db")) as db:
    db.set(Hero).where(lambda h: (h.age > 30) & (h.team_id == 1)).order_by(lambda h: h.name).take(10).to_list()
    # SELECT ... FROM hero WHERE hero.age > 30 AND hero.team_id = 1 ORDER BY hero.name LIMIT 10

    db.set(Hero).group_by(lambda h: h.team_id).select(lambda g: (g.key, g.count(), g.average(lambda h: h.age))).to_list()
    # SELECT hero.team_id, count(*), avg(hero.age) FROM hero GROUP BY hero.team_id

    db.set(Hero).include(lambda h: h.team).first(lambda h: h.name == "Tony")
    db.set(Hero).where(lambda h: h.age > 100).execute_update(lambda h: {h.age: h.age + 1})

async with DbContext(create_async_engine("sqlite+aiosqlite:///app.db")) as db:
    adults = await db.set(Hero).where(lambda h: h.age >= 18).to_list_async()
```

A lambda is called with the model class, so it builds a SQLAlchemy expression. Combine conditions with `&`, `|` and `~`, not `and`, `or` and `not`. A `select` SQL can't express runs in memory, as EF's client projection does, and so does every operator EF doesn't translate. The [Entity Framework guide](https://codejunction.github.io/pydantic-linq/orm/) maps each EF Core feature.

## Conventions

- Wrap any iterable in `Enumerable(...)` (or `AsyncEnumerable(...)`) to query it. Every operator is typed, so editors and type checkers see them. The package doesn't patch builtins.
- Method names are the C# names in snake_case: `OrderByDescending` becomes `order_by_descending`. `Except` becomes `except_`, because `except` is a Python keyword. The [operator map](https://codejunction.github.io/pydantic-linq/operators/) lists every operator.
- Operators that return a sequence are deferred and can be enumerated again, as in .NET.
- Equality uses value semantics (`==`). Non-frozen (unhashable) pydantic models work in `distinct`, `union` and the other set operators.
- `cast(Model)` validates each element with a pydantic `TypeAdapter`, so dicts become models. `of_type(Model)` filters with `isinstance`.
- `Enumerable[Model]` can be a pydantic field type. It validates like `list[Model]` and serializes as a list.
- `group_by` yields `Grouping` objects. Each is itself an `Enumerable` with a `.key`.
- C# `KeyValuePair` becomes a `(key, value)` tuple. `IComparer` becomes a `cmp(a, b) -> int` function. A C# `Range` or `Index` (for example `^1`) becomes a slice or a negative int.
- Lambda overloads that take an index (`Select((x, i) => ...)`) map to `.index()`, followed by the operator.
- Empty-sequence errors raise `InvalidOperationError`, which subclasses `ValueError`.

## Examples

`examples/` runs from simple to complex: `01_basics` through `07_sales_report`, an end-to-end report pipeline, then `08_entity_framework` and `09_entity_framework_async` for database queries. `fastapi_blog/` is a full FastAPI blog post API over SQLite. Run any of them with `uv run python examples/01_basics.py`.

## Layout

```
src/pydantic_linq/
  core/           errors, value-equality set, group and sort helpers (no internal deps)
  sync/
    base.py       EnumerableBase, deferred execution
    operators/    one mixin per LINQ category: filtering, projection, partitioning, sets, sorting, ...
    enumerable.py Enumerable = all mixins
    ordered.py    OrderedEnumerable (then_by)
    grouping.py   Grouping (an Enumerable with .key), Lookup
  aio/            AsyncEnumerable, same layout as sync/
  integrations/   pydantic field schema
  orm/            Entity Framework over SQLModel: Queryable, DbContext (optional extra)
docs/             documentation site (MkDocs); the API reference is generated from the docstrings
```

## Contributing

Every code change also updates `CHANGELOG.md` (under `[Unreleased]`) and the docs in `docs/`. See [CLAUDE.md](CLAUDE.md) for the checks and the release steps.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
