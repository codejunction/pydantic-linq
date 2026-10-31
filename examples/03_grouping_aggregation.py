"""Grouping and aggregation: GroupBy, ToLookup, CountBy, AggregateBy, Sum / Average / MaxBy."""

from datetime import date

from pydantic import BaseModel

from pydantic_linq import Enumerable


class Sale(BaseModel):
    region: str
    rep: str
    amount: float
    day: date


sales = Enumerable([
    Sale(region="North", rep="Ann", amount=120.0, day=date(2026, 1, 3)),
    Sale(region="North", rep="Bob", amount=80.0, day=date(2026, 1, 4)),
    Sale(region="South", rep="Cid", amount=200.0, day=date(2026, 1, 4)),
    Sale(region="North", rep="Ann", amount=60.0, day=date(2026, 2, 1)),
    Sale(region="South", rep="Dee", amount=40.0, day=date(2026, 2, 2)),
])

# GroupBy with a result selector: one summary row per region
summary = sales.group_by(
    lambda s: s.region,
    result_selector=lambda region, items: (region, items.count(), items.sum(lambda s: s.amount)),
).to_list()
print("region, orders, total:", summary)

# Each Grouping is itself an Enumerable with a .key
for g in sales.group_by(lambda s: s.day.month):
    print(f"month {g.key}: avg {g.average(lambda s: s.amount):.2f}, reps {g.select(lambda s: s.rep).distinct().to_list()}")

# A Lookup is an indexable group set; a missing key gives an empty sequence
by_rep = sales.to_lookup(lambda s: s.rep, lambda s: s.amount)
print("Ann:", by_rep["Ann"].to_list(), "Zed:", by_rep["Zed"].to_list())

# .NET 9 CountBy / AggregateBy
print("orders per rep:", sales.count_by(lambda s: s.rep).to_list())
print("revenue per rep:", sales.aggregate_by(lambda s: s.rep, 0.0, lambda acc, s: acc + s.amount).to_list())

# Scalar aggregates
print("total:", sales.sum(lambda s: s.amount))
print("biggest sale:", sales.max_by(lambda s: s.amount).rep)
print("running product:", Enumerable([1, 2, 3, 4]).aggregate(lambda a, b: a * b))
