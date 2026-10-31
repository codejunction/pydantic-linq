import asyncio

import pytest
from pydantic import BaseModel

from pydantic_linq import AsyncEnumerable, Enumerable, InvalidOperationError

A = AsyncEnumerable


class Person(BaseModel):
    name: str
    age: int
    city: str


PEOPLE = [
    Person(name="Ann", age=31, city="Oslo"),
    Person(name="Bob", age=25, city="Rome"),
    Person(name="Cid", age=31, city="Oslo"),
    Person(name="Dee", age=19, city="Lima"),
]


async def agen(items):
    for x in items:
        await asyncio.sleep(0)
        yield x


async def age_of(p):  # async selector, the *Await overload
    await asyncio.sleep(0)
    return p.age


def run(coro):
    return asyncio.run(coro)


def test_sources_selectors_and_reenumeration():
    q = A(PEOPLE).where(lambda p: p.age > 20).select(age_of)
    assert run(q.to_list()) == [31, 25, 31]
    assert run(q.to_list()) == [31, 25, 31]
    assert run(A(agen([1, 2])).select(str).to_list()) == ["1", "2"]
    assert run(Enumerable(PEOPLE).to_async_enumerable().count()) == 4


def test_generation_projection_partitioning():
    assert run(A.range(1, 3).concat(agen([9])).append(10).prepend(0).to_list()) == [0, 1, 2, 3, 9, 10]
    assert run(A.repeat("x", 2).to_list()) == ["x", "x"]
    assert run(A.empty().default_if_empty(7).to_list()) == [7]
    assert run(A(["ab", "c"]).select_many(lambda s: agen(s)).to_list()) == ["a", "b", "c"]
    assert run(A("xy").index().to_list()) == [(0, "x"), (1, "y")]
    assert run(A([1, 2, 3]).zip(agen("ab")).to_list()) == [(1, "a"), (2, "b")]
    assert run(A([1, 2]).zip_with([10, 20], lambda a, b: a + b).to_list()) == [11, 22]
    s = A(range(10))
    assert run(s.take(3).to_list()) == [0, 1, 2]
    assert run(s.take(slice(2, 8, 3)).to_list()) == [2, 5]
    assert run(s.take(slice(-2, None)).to_list()) == [8, 9]
    assert run(s.skip(8).to_list()) == [8, 9]
    assert run(s.take_while(lambda x: x < 2).to_list()) == [0, 1]
    assert run(s.skip_while(lambda x: x < 8).to_list()) == [8, 9]
    assert run(s.take_last(2).to_list()) == [8, 9]
    assert run(s.skip_last(8).to_list()) == [0, 1]
    assert run(s.chunk(4).to_list()) == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]


def test_sets_with_models():
    dup = [*PEOPLE, Person(name="Ann", age=31, city="Oslo")]
    assert len(run(A(dup).distinct().to_list())) == 4
    assert run(A([1, 2, 2]).union(agen([3, 1])).to_list()) == [1, 2, 3]
    assert run(A([1, 2, 2, 3]).intersect([2, 3, 4]).to_list()) == [2, 3]
    assert run(A([1, 2, 2, 3]).except_([3]).to_list()) == [1, 2]
    assert run(A(PEOPLE).distinct_by(age_of).select(lambda p: p.name).to_list()) == ["Ann", "Bob", "Dee"]


def test_ordering_with_async_keys():
    q = A(PEOPLE).order_by_descending(age_of).then_by(lambda p: p.name).select(lambda p: p.name)
    assert run(q.to_list()) == ["Ann", "Cid", "Bob", "Dee"]
    assert run(A([3, 1, 2]).order().to_list()) == [1, 2, 3]
    assert run(A([3, 1, 2]).order_descending().to_list()) == [3, 2, 1]
    assert run(A([1, 2, 3]).reverse().to_list()) == [3, 2, 1]


def test_grouping_and_joins():
    q = A(PEOPLE).group_by(lambda p: p.city, age_of, result_selector=lambda k, ages: ages.sum())
    assert run(q.to_list()) == [62, 25, 19]
    lookup = run(A(PEOPLE).to_lookup(lambda p: p.city, lambda p: p.name))
    assert lookup["Oslo"].to_list() == ["Ann", "Cid"]
    orders = [("Ann", 10), ("Ann", 5), ("Eve", 1)]
    j = A(PEOPLE).join(orders, lambda p: p.name, lambda o: o[0], lambda p, o: (p.name, o[1]))
    assert run(j.to_list()) == [("Ann", 10), ("Ann", 5)]
    gj = A(PEOPLE[:2]).group_join(orders, lambda p: p.name, lambda o: o[0], lambda p, os: os.count())
    assert run(gj.to_list()) == [2, 0]
    lj = A(PEOPLE[:2]).left_join(orders, lambda p: p.name, lambda o: o[0], lambda p, o: o and o[1])
    assert run(lj.to_list()) == [10, 5, None]
    rj = A(PEOPLE[:1]).right_join(orders, lambda p: p.name, lambda o: o[0], lambda p, o: p and p.name)
    assert run(rj.to_list()) == ["Ann", "Ann", None]


def test_element_quantifiers_equality():
    s = A([1, 2, 3])
    assert run(s.first()) == 1 and run(s.last(lambda x: x < 3)) == 2
    assert run(s.single(lambda x: x == 2)) == 2 and run(s.single_or_default(lambda x: x > 5)) is None
    assert run(s.element_at(-1)) == 3 and run(s.element_at_or_default(9)) is None
    assert run(s.any()) and not run(A([]).any()) and run(s.all(lambda x: x > 0)) and run(s.contains(2))
    assert run(s.sequence_equal(agen([1, 2, 3]))) and not run(s.sequence_equal([1, 2]))
    with pytest.raises(InvalidOperationError, match="no elements"):
        run(A([]).first())
    with pytest.raises(InvalidOperationError, match="more than one"):
        run(s.single())
    with pytest.raises(IndexError):
        run(s.element_at(5))


def test_aggregation_and_conversion():
    s = A(PEOPLE)
    assert run(s.count(lambda p: p.city == "Oslo")) == 2
    assert run(s.sum(age_of)) == 106 and run(s.average(age_of)) == 26.5
    assert run(s.min(age_of)) == 19 and run(s.max(age_of)) == 31
    assert run(s.min_by(age_of)).name == "Dee" and run(s.max_by(age_of)).name == "Ann"
    assert run(A([1, 2, 3]).aggregate(lambda a, b: a * b)) == 6
    assert run(A([1, 2, 3]).aggregate(0, lambda a, b: a + b, str)) == "6"
    assert run(s.count_by(lambda p: p.city).to_list()) == [("Oslo", 2), ("Rome", 1), ("Lima", 1)]
    assert run(s.to_dictionary(lambda p: p.name, age_of))["Bob"] == 25
    assert run(A([{"name": "Z", "age": "4", "city": "K"}]).cast(Person).first()).age == 4
    with pytest.raises(InvalidOperationError):
        run(A([]).average())
    with pytest.raises(InvalidOperationError):
        run(A([]).max_by(abs))
