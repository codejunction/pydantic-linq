"""Async Entity Framework style queries: an AsyncEngine and EF's *Async terminal operators.

Needs the extra and an async driver: pip install pydantic-linq[sqlmodel] aiosqlite
"""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel

from pydantic_linq.orm import DbContext


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer: str
    total: float


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with DbContext(engine) as db:
        await db.ensure_created_async()
        db.add_range(
            Order(customer=c, total=t)
            for c, t in [("ann", 40.0), ("bob", 15.5), ("ann", 99.9), ("cid", 12.0), ("bob", 70.0)]
        )
        await db.save_changes_async()

        orders = db.set(Order)
        print("big orders:", await orders.where(lambda o: o.total > 50).count_async())
        print("first:", (await orders.order_by(lambda o: o.total).first_async()).customer)
        print("revenue:", await orders.sum_async(lambda o: o.total))

        by_customer = orders.group_by(lambda o: o.customer).select(lambda g: (g.key, g.sum(lambda o: o.total)))
        print("by customer:", await by_customer.to_dictionary_async(lambda kv: kv[0], lambda kv: kv[1]))

        # AsAsyncEnumerable: continue with System.Linq.Async operators in memory.
        print("chunks:", await orders.order_by(lambda o: o.id).as_async_enumerable().chunk(2).count())

        async def notify(order: Order) -> None:
            await asyncio.sleep(0)
            print("  notify", order.customer, order.total)

        await orders.where(lambda o: o.customer == "ann").for_each_async(notify)
        print("deleted:", await orders.where(lambda o: o.total < 20).execute_delete_async())
        await db.save_changes_async()
    await engine.dispose()


asyncio.run(main())
