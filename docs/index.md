# pydantic-linq

C# LINQ for Python. It has every `System.Linq` and `System.Linq.Async` operator, is fully typed, and works with Pydantic models.

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

rows.where(lambda r: r.tag == "a").select(lambda r: r.id).to_list()         # [1, 3]
rows.group_by(lambda r: r.tag).select(lambda g: (g.key, g.count())).to_list()  # [('a', 2), ('b', 1)]
```

## Why

- **The same API as C#.** The names are the C# names in snake_case: `OrderByDescending` becomes `order_by_descending`. The overloads and the error behavior match the C# ones. See the [operator map](operators.md).
- **Deferred and re-enumerable.** A query does nothing until you enumerate it, and you can enumerate it again, as in .NET.
- **Typed.** Generics flow through every operator, so `rows.select(lambda r: r.id)` is an `Enumerable[int]` to pyright and mypy.
- **Pydantic-aware.** `cast(Model)` validates raw dicts. `Enumerable[Model]` works as a field type. The set operators compare models by value. See [Pydantic](pydantic.md).
- **Entity Framework too.** `pydantic_linq.orm` runs the same LINQ as SQL through SQLModel, with `DbContext`, `include`, `execute_update` and the `*_async` operators. See [Entity Framework](orm.md).
- **Async too.** `AsyncEnumerable` takes sync or async sources and sync or async selectors. See [Async](async.md).

## Next

- [Getting started](getting-started.md)
- [Examples](examples.md), from simple to complex
- [API reference](api/enumerable.md)
