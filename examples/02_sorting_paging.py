"""Sorting and paging: OrderBy / ThenBy, Skip / Take, Chunk."""

from pydantic import BaseModel

import pydantic_linq  # noqa: F401


class Employee(BaseModel):
    name: str
    dept: str
    salary: int


staff = [
    Employee(name="Ava", dept="Eng", salary=120),
    Employee(name="Ben", dept="Ops", salary=90),
    Employee(name="Cleo", dept="Eng", salary=120),
    Employee(name="Dan", dept="Eng", salary=105),
    Employee(name="Eve", dept="Ops", salary=95),
]

# Multi-key, stable sort: dept ascending, then salary descending, then name
ordered = staff.order_by(lambda e: e.dept).then_by_descending(lambda e: e.salary).then_by(lambda e: e.name)
print([f"{e.dept}:{e.name}:{e.salary}" for e in ordered])

# Paging
page_size = 2
for page in range(3):
    names = ordered.skip(page * page_size).take(page_size).select(lambda e: e.name).to_list()
    print(f"page {page + 1}:", names)

# Chunk does the same in one call
print("chunks:", ordered.select(lambda e: e.name).chunk(2).to_list())

# Take with a range: slice(1, -1) is C#'s Take(1..^1)
print("without top and bottom:", ordered.take(slice(1, -1)).select(lambda e: e.name).to_list())
