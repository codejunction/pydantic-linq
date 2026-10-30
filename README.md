# pydantic-linq

C# LINQ (`System.Linq.Enumerable`) for Python. It is typed and works with Pydantic.

```python
from pydantic import BaseModel
import pydantic_linq  # adds LINQ operators to list / tuple / set / frozenset

class Row(BaseModel):
    id: int
    tag: str

rows = [Row(id=1, tag="a"), Row(id=2, tag="b"), Row(id=3, tag="a")]

rows.where(lambda r: r.tag == "a").select(lambda r: r.id).to_list()   # [1, 3]
rows.group_by(lambda r: r.tag).select(lambda g: (g.key, len(g))).to_list()
rows.order_by_descending(lambda r: r.id).then_by(lambda r: r.tag).first()
```

## Async

`AsyncEnumerable` covers System.Linq.Async. It wraps any sync or async iterable. Sequence operators are deferred, and terminal operators are awaited:

```python
async def load_age(r: Row) -> int: ...

ages = await rows.to_async_enumerable().where(lambda r: r.id > 1).select(load_age).to_list()
```

A selector or predicate can be a plain function or an `async def`, so there are no separate `*Await` overloads. Terminal operators keep the sync names (`to_list`, `first`, `count`) and are awaited. The C# `Async` suffix is dropped.

## Conventions

- Method names are the C# names in snake_case: `OrderByDescending` becomes `order_by_descending`. `Except` becomes `except_`, because `except` is a Python keyword.
- Operators that return a sequence are deferred and can be enumerated again, as in .NET.
- Equality uses value semantics (`==`). Non-frozen (unhashable) pydantic models work in `distinct`, `union` and the other set operators.
- `cast(Model)` validates each element with a pydantic `TypeAdapter`, so dicts become models. `of_type(Model)` filters with `isinstance`.
- `Enumerable[Model]` can be a pydantic field type. It validates like `list[Model]` and serializes as a list.
- C# `KeyValuePair` becomes a `(key, value)` tuple. `IComparer` becomes a `cmp(a, b) -> int` function. A C# `Range` or `Index` (for example `^1`) becomes a slice or a negative int.
- Lambda overloads that take an index (`Select((x, i) => ...)`) map to `.index()`, followed by the operator.
- Empty-sequence errors raise `InvalidOperationError`, which subclasses `ValueError`.

## Builtin patching

Importing the package uses [forbiddenfruit](https://github.com/clarete/forbiddenfruit) to patch `list`, `tuple`, `set` and `frozenset`. A builtin method that already exists keeps its Python meaning, for example `list.count(x)` and `list.reverse()`. To get the LINQ version, use `rows.as_enumerable().count()`. Type checkers do not see the patched methods. Where you need static types, use `Enumerable(rows)`. To remove the patches, call `pydantic_linq.uninstall()`.

## Layout

```
src/pydantic_linq/
  core/           errors, value-equality set, Grouping (no internal deps)
  sync/
    base.py       EnumerableBase, deferred execution
    operators/    one mixin per LINQ category: filtering, projection, partitioning, sets, sorting, ...
    enumerable.py Enumerable = all mixins
    ordered.py    OrderedEnumerable (then_by)
    lookup.py     Lookup
  aio/            AsyncEnumerable, same layout as sync/
  integrations/   pydantic field schema, builtin patching
```

## Examples

`examples/` runs from simple to complex: `01_basics` through `07_sales_report`, an end-to-end report pipeline. Run any of them with `uv run python examples/01_basics.py`.

