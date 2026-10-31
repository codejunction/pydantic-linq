# Getting started

## Install

```bash
pip install pydantic-linq
# or
uv add pydantic-linq
```

You need Python 3.12 or later and Pydantic 2.

For [Entity Framework style database queries](orm.md) through SQLModel, install the extra: `pip install "pydantic-linq[sqlmodel]"`.

## Wrap any iterable

`Enumerable(...)` takes a list, tuple, set, generator or any other iterable. Every operator is typed, so your editor and type checker see the methods and the element types:

```python
from pydantic_linq import Enumerable

Enumerable([3, 1, 2]).order().to_list()                  # [1, 2, 3]
Enumerable(range(10)).where(lambda x: x % 2 == 0).sum()  # 20
```

For async sources and async selectors, use `AsyncEnumerable(...)` the same way. See [Async](async.md).

## Deferred execution

Operators that return a sequence don't run until you enumerate them, and every enumeration runs the query again:

```python
items = [1, 2, 3]
evens = Enumerable(items).where(lambda x: x % 2 == 0)
items.append(4)
evens.to_list()  # [2, 4]
```

Terminal operators run the query right away. These include `to_list`, `first`, `count`, `sum`, `any` and `to_dictionary`.

## Errors

| Situation | C# | pydantic-linq |
|---|---|---|
| `first()` / `single()` / `min()` / `average()` / `aggregate(func)` on an empty sequence | `InvalidOperationException` | `InvalidOperationError` (a `ValueError`) |
| `single()` with more than one match | `InvalidOperationException` | `InvalidOperationError` |
| `element_at()` out of range | `ArgumentOutOfRangeException` | `IndexError` |
| `to_dictionary()` with a duplicate key | `ArgumentException` | `ValueError` |

The `*_or_default` variants return `default` (`None` unless you pass one) instead of raising.
