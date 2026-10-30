"""Joins and set operations across two model lists."""

from pydantic import BaseModel

import pydantic_linq  # noqa: F401


class Customer(BaseModel):
    id: int
    name: str


class Order(BaseModel):
    customer_id: int
    item: str


customers = [Customer(id=1, name="Ann"), Customer(id=2, name="Bob"), Customer(id=3, name="Cid")]
orders = [
    Order(customer_id=1, item="book"),
    Order(customer_id=1, item="pen"),
    Order(customer_id=3, item="lamp"),
    Order(customer_id=9, item="ghost"),
]

# Inner join
print("join:", customers.join(orders, lambda c: c.id, lambda o: o.customer_id, lambda c, o: (c.name, o.item)).to_list())

# GroupJoin: every customer with their orders (possibly none)
print(
    "group join:",
    customers.group_join(
        orders, lambda c: c.id, lambda o: o.customer_id, lambda c, os: (c.name, os.select(lambda o: o.item).to_list())
    ).to_list(),
)

# .NET 10 LeftJoin / RightJoin: the missing side is None
print(
    "left join:",
    customers.left_join(
        orders, lambda c: c.id, lambda o: o.customer_id, lambda c, o: (c.name, o.item if o else None)
    ).to_list(),
)
print(
    "right join:",
    customers.right_join(
        orders, lambda c: c.id, lambda o: o.customer_id, lambda c, o: (c.name if c else None, o.item)
    ).to_list(),
)

# Set operations use value equality, so equal (non-frozen) models count as duplicates
batch_a = [Customer(id=1, name="Ann"), Customer(id=2, name="Bob")]
batch_b = [Customer(id=2, name="Bob"), Customer(id=4, name="Dee")]
print("union:", batch_a.union(batch_b).select(lambda c: c.name).to_list())
print("intersect:", batch_a.intersect(batch_b).select(lambda c: c.name).to_list())
print("except:", batch_a.except_(batch_b).select(lambda c: c.name).to_list())

# *By variants compare by a key; the second sequence holds keys
print("customers without orders:", customers.except_by(orders.select(lambda o: o.customer_id), lambda c: c.id)
      .select(lambda c: c.name).to_list())
