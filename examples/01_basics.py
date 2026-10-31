"""Basics: filter, project and pick elements from a plain list of pydantic models."""

from pydantic import BaseModel

from pydantic_linq import Enumerable


class Product(BaseModel):
    name: str
    price: float
    stock: int


catalog = [
    Product(name="Keyboard", price=49.0, stock=12),
    Product(name="Mouse", price=19.5, stock=0),
    Product(name="Monitor", price=219.0, stock=4),
    Product(name="Cable", price=5.0, stock=120),
]
products = Enumerable(catalog)  # wrap any iterable; every operator is typed

# Where + Select
in_stock = products.where(lambda p: p.stock > 0).select(lambda p: p.name).to_list()
print("in stock:", in_stock)

# Element operators
print("first over $100:", products.first(lambda p: p.price > 100).name)
print("first over $1000:", products.first_or_default(lambda p: p.price > 1000))

# Quantifiers and counting
print("any sold out:", products.any(lambda p: p.stock == 0))
print("sold out count:", products.count(lambda p: p.stock == 0))

# Queries are deferred: nothing runs until you enumerate, so later changes to the list show up
cheap = products.where(lambda p: p.price < 20)
catalog.append(Product(name="Sticker", price=1.0, stock=500))
print("cheap (evaluated now):", cheap.select(lambda p: p.name).to_list())
