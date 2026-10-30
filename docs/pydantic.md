# Pydantic

## `cast(Model)`: validate raw data

C# `Cast<T>` only casts references. Here `cast` validates each element with a pydantic `TypeAdapter`, so dicts become models and values are coerced:

```python
raw = [{"sku": "A-1", "qty": "2"}]
items = raw.cast(LineItem).to_list()          # [LineItem(sku='A-1', qty=2)]
raw.cast(LineItem, strict=True).to_list()     # raises ValidationError: no coercion
```

`cast` accepts any type a `TypeAdapter` takes: `int`, `datetime`, `list[Model]`, `Model | None`, and so on.

`of_type(Model)` is the plain `isinstance` filter (`OfType<T>`).

## `Enumerable[Model]` as a field type

```python
from pydantic import BaseModel
from pydantic_linq import Enumerable

class Invoice(BaseModel):
    lines: Enumerable[LineItem]

inv = Invoice.model_validate({"lines": [{"sku": "A-1", "qty": 2}]})
inv.lines.sum(lambda l: l.qty)   # LINQ on the field
inv.model_dump()                 # {'lines': [{'sku': 'A-1', 'qty': 2}]}
```

- Validation is the same as for `list[LineItem]`: the same coercion, errors and JSON schema (`"type": "array"`).
- It serializes as a plain list.
- An existing `Enumerable` is accepted as input too.

## Value equality

Non-frozen pydantic models compare by field values (`==`) but are unhashable. The set operators (`distinct`, `union`, `intersect`, `except_` and their `*_by` forms) and `contains` all use value equality, so they work on such models directly:

```python
[Item(id=1), Item(id=1)].distinct().count()  # 1
```

!!! tip "Performance"
    Unhashable items fall back to a linear scan. For large sets, use `frozen=True` models (hashable) or a `*_by` key that returns a hashable value, such as an id.
