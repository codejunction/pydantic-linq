# Builtin patching

`import pydantic_linq` uses [forbiddenfruit](https://github.com/clarete/forbiddenfruit) to add every `Enumerable` operator to `list`, `tuple`, `set` and `frozenset`. Each patched method wraps the collection in an `Enumerable` and returns what that call returns.

```python
import pydantic_linq

rows.where(lambda r: r.active).select(lambda r: r.id).to_list()
```

## Name clashes

When a builtin already has a method with that name, the builtin wins:

| Builtin method | Meaning kept | LINQ version |
|---|---|---|
| `list.count(x)`, `tuple.count(x)` | occurrences of `x` | `rows.as_enumerable().count()` |
| `list.index(x)` | position of `x` | `rows.as_enumerable().index()` |
| `list.reverse()` | reverses in place | `rows.as_enumerable().reverse()` |
| `list.append(x)` | appends in place | `rows.as_enumerable().append(x)` |
| `set.union(...)` | Python union | `s.as_enumerable().union(...)` |

## Typing

Type checkers can't see methods added at runtime. Where you want static types, use `Enumerable(rows)`. Every operator on it is fully typed.

## Turning it off

```python
pydantic_linq.uninstall()   # remove the patched methods
pydantic_linq.install()     # add them back (idempotent)
```

forbiddenfruit works on CPython only.
