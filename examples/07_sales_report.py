"""End to end: raw JSON in, validated models, async enrichment, joins, grouping, a typed report out."""

import asyncio
import json
from datetime import date

from pydantic import BaseModel

from pydantic_linq import Enumerable

RAW_ORDERS = json.loads("""[
  {"id": 1, "customer": "acme",   "sku": "W-1", "qty": 3,  "day": "2026-03-01"},
  {"id": 2, "customer": "globex", "sku": "G-9", "qty": 1,  "day": "2026-03-01"},
  {"id": 3, "customer": "acme",   "sku": "G-9", "qty": 2,  "day": "2026-03-02"},
  {"id": 4, "customer": "initech","sku": "W-1", "qty": 10, "day": "2026-03-03"},
  {"id": 5, "customer": "acme",   "sku": "X-0", "qty": 1,  "day": "2026-03-03"},
  {"id": 2, "customer": "globex", "sku": "G-9", "qty": 1,  "day": "2026-03-01"}
]""")


class Order(BaseModel):
    id: int
    customer: str
    sku: str
    qty: int
    day: date


class Product(BaseModel):
    sku: str
    name: str
    price: float


class CustomerRow(BaseModel):
    customer: str
    orders: int
    revenue: float
    top_product: str


class Report(BaseModel):
    rows: Enumerable[CustomerRow]
    unknown_skus: list[str]
    best_day: date


CATALOG = [Product(sku="W-1", name="Widget", price=4.5), Product(sku="G-9", name="Gadget", price=30.0)]


async def price_lookup(sku: str) -> float | None:
    """Pretend pricing service; async so it shows the async layer."""
    await asyncio.sleep(0.01)
    return {"W-1": 4.0, "G-9": 28.0}.get(sku)  # live price, may differ from the catalog


async def build_report() -> Report:
    # 1. Validate the raw JSON and drop duplicate records (value equality on models)
    orders = Enumerable(RAW_ORDERS).cast(Order).distinct().to_list()

    # 2. SKUs with no catalog entry: except_by against the catalog keys
    unknown = orders.except_by(CATALOG.select(lambda p: p.sku), lambda o: o.sku).select(lambda o: o.sku).to_list()

    # 3. Join to the catalog; live price from the async service, catalog price as fallback
    async def priced(pair: tuple[Order, Product]) -> tuple[Order, Product, float]:
        order, product = pair
        live = await price_lookup(product.sku)
        return order, product, live if live is not None else product.price

    lines = await (
        orders.join(CATALOG, lambda o: o.sku, lambda p: p.sku, lambda o, p: (o, p))
        .to_async_enumerable()
        .select(priced)
        .to_list()
    )

    # 4. Per-customer rows, highest revenue first
    rows = (
        lines.group_by(lambda line: line[0].customer)
        .select(
            lambda g: CustomerRow(
                customer=g.key,
                orders=g.count(),
                revenue=g.sum(lambda line: line[0].qty * line[2]),
                top_product=g.max_by(lambda line: line[0].qty * line[2])[1].name,
            )
        )
        .order_by_descending(lambda r: r.revenue)
        .then_by(lambda r: r.customer)
        .to_list()
    )

    # 5. Day with the most units shipped
    best_day = orders.aggregate_by(lambda o: o.day, 0, lambda n, o: n + o.qty).max_by(lambda kv: kv[1])[0]

    return Report(rows=rows, unknown_skus=unknown, best_day=best_day)


report = asyncio.run(build_report())
print(report.model_dump_json(indent=2))
