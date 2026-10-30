"""Basics: filter, project and pick elements from a plain list of pydantic models."""

from pydantic import BaseModel

import pydantic_linq  # noqa: F401  (adds the LINQ operators to list / tuple / set)
from pydantic_linq import Enumerable


class Product(BaseModel):
    name: str
    price: float
    stock: int


products = [
    Product(name="Keyboard", price=49.0, stock=12),
    Product(name="Mouse", price=19.5, stock=0),
    Product(name="Monitor", price=219.0, stock=4),
    Product(name="Cable", price=5.0, stock=120),
]

# Where + Select, called straight on the list
in_stock = products.where(lambda p: p.stock > 0).select(lambda p: p.name).to_list()
print("in stock:", in_stock)

# Element operators
print("first over $100:", products.first(lambda p: p.price > 100).name)
print("first over $1000:", products.first_or_default(lambda p: p.price > 1000))

# Quantifiers and counting. list.count(x) keeps its Python meaning, so wrap for the LINQ count().
print("any sold out:", products.any(lambda p: p.stock == 0))
print("sold out count:", Enumerable(products).count(lambda p: p.stock == 0))

# Queries are deferred: nothing runs until you enumerate
cheap = products.where(lambda p: p.price < 20)
products.append(Product(name="Sticker", price=1.0, stock=500))
print("cheap (evaluated now):", cheap.select(lambda p: p.name).to_list())
