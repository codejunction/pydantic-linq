"""Pydantic integration: validate raw data with cast(), use Enumerable[Model] as a field, round-trip JSON."""

from pydantic import BaseModel, ValidationError

from pydantic_linq import Enumerable


class LineItem(BaseModel):
    sku: str
    qty: int
    unit_price: float


class Invoice(BaseModel):
    number: str
    lines: Enumerable[LineItem]  # validated like list[LineItem]; behaves like LINQ

    @property
    def total(self) -> float:
        return self.lines.sum(lambda line: line.qty * line.unit_price)


# Raw rows, e.g. from an API or CSV: strings get coerced, dicts become models
raw = Enumerable([
    {"sku": "A-1", "qty": "2", "unit_price": "9.99"},
    {"sku": "B-7", "qty": 1, "unit_price": 120},
])
items = raw.cast(LineItem).to_list()
print("cast:", items)

# strict=True disables coercion
try:
    raw.cast(LineItem, strict=True).to_list()
except ValidationError as e:
    print("strict cast failed:", e.error_count(), "errors")

invoice = Invoice(number="INV-1", lines=Enumerable(items))
print("total:", round(invoice.total, 2))
print("big lines:", invoice.lines.where(lambda line: line.unit_price > 50).select(lambda line: line.sku).to_list())

# Serializes as a plain list; validates back into an Enumerable
payload = invoice.model_dump_json()
print("json:", payload)
again = Invoice.model_validate_json(payload)
print("round-trip type:", type(again.lines).__name__, "count:", again.lines.count())

# Value equality: non-frozen models are unhashable, distinct() still works
dupes = [LineItem(sku="A-1", qty=1, unit_price=1.0)] * 3
print("distinct:", Enumerable(dupes).distinct().count())

# of_type filters by class, like OfType<T>
mixed = [items[0], "noise", 42, items[1]]
print("of_type:", Enumerable(mixed).of_type(LineItem).select(lambda line: line.sku).to_list())
