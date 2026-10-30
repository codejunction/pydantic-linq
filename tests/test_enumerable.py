import pytest
from pydantic import BaseModel, ValidationError

from pydantic_linq import Enumerable, InvalidOperationError


class Person(BaseModel):
    name: str
    age: int
    city: str


class Order(BaseModel):
    person: str
    total: float


PEOPLE = [
    Person(name="Ann", age=31, city="Oslo"),
    Person(name="Bob", age=25, city="Rome"),
    Person(name="Cid", age=31, city="Oslo"),
    Person(name="Dee", age=19, city="Lima"),
]
ORDERS = [Order(person="Ann", total=10), Order(person="Ann", total=5), Order(person="Cid", total=7)]

E = Enumerable


def names(seq):
    return [p.name for p in seq]


def test_deferred_and_reenumerable():
    calls = []
    q = E([1, 2, 3]).select(lambda x: calls.append(x) or x * 2)
    assert calls == []
    assert q.to_list() == [2, 4, 6]
    assert q.to_list() == [2, 4, 6]
    assert calls == [1, 2, 3, 1, 2, 3]


def test_generation():
    assert E.range(3, 4).to_list() == [3, 4, 5, 6]
    assert E.repeat("x", 2).to_list() == ["x", "x"]
    assert E.empty().to_list() == []
    assert E.sequence(10, 4, -3).to_list() == [10, 7, 4]
    assert E.infinite_sequence(0, 5).take(3).to_list() == [0, 5, 10]
    with pytest.raises(ValueError):
        E.range(0, -1)


def test_where_select_select_many_index():
    adults = E(PEOPLE).where(lambda p: p.age > 20).select(lambda p: p.name)
    assert adults.to_list() == ["Ann", "Bob", "Cid"]
    assert E(["ab", "c"]).select_many(list).to_list() == ["a", "b", "c"]
    assert E(["ab"]).select_many(list, lambda s, c: s + c).to_list() == ["aba", "abb"]
    assert E("xy").index().to_list() == [(0, "x"), (1, "y")]


def test_cast_validates_with_pydantic_and_of_type():
    people = E([{"name": "Zed", "age": "40", "city": "Kyiv"}]).cast(Person).to_list()
    assert people == [Person(name="Zed", age=40, city="Kyiv")]
    with pytest.raises(ValidationError):
        E([{"name": "Zed", "age": "40", "city": "Kyiv"}]).cast(Person, strict=True).to_list()
    assert E([1, "a", 2.0, PEOPLE[0]]).of_type(Person).to_list() == [PEOPLE[0]]


def test_partitioning():
    s = E(range(10))
    assert s.take(3).to_list() == [0, 1, 2]
    assert s.take(-1).to_list() == []
    assert s.take(slice(2, -6)).to_list() == [2, 3]
    assert s.take(slice(-2, None)).to_list() == [8, 9]
    assert s.skip(8).to_list() == [8, 9]
    assert s.take_while(lambda x: x < 2).to_list() == [0, 1]
    assert s.skip_while(lambda x: x < 8).to_list() == [8, 9]
    assert s.take_last(2).to_list() == [8, 9]
    assert s.skip_last(8).to_list() == [0, 1]
    assert s.chunk(4).to_list() == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]
    with pytest.raises(ValueError):
        s.chunk(0)


def test_concat_append_prepend_default_if_empty():
    assert E([1]).concat([2]).append(3).prepend(0).to_list() == [0, 1, 2, 3]
    assert E([]).default_if_empty(7).to_list() == [7]
    assert E([1]).default_if_empty(7).to_list() == [1]


def test_set_operators_with_unhashable_models():
    dup = [*PEOPLE, Person(name="Ann", age=31, city="Oslo")]
    assert names(E(dup).distinct()) == ["Ann", "Bob", "Cid", "Dee"]
    assert names(E(PEOPLE).distinct_by(lambda p: p.city)) == ["Ann", "Bob", "Dee"]
    assert E([1, 2, 2]).union([3, 1]).to_list() == [1, 2, 3]
    assert names(E(PEOPLE[:2]).union_by(PEOPLE, lambda p: p.city)) == ["Ann", "Bob", "Dee"]
    assert E([1, 2, 2, 3]).intersect([2, 3, 4]).to_list() == [2, 3]
    assert names(E(PEOPLE).intersect_by(["Oslo"], lambda p: p.city)) == ["Ann"]
    assert E([1, 2, 2, 3]).except_([3]).to_list() == [1, 2]
    assert names(E(PEOPLE).except_by(["Oslo"], lambda p: p.city)) == ["Bob", "Dee"]


def test_ordering_is_stable_and_multi_key():
    q = E(PEOPLE).order_by_descending(lambda p: p.age).then_by(lambda p: p.name, lambda a, b: (a < b) - (a > b))
    assert names(q) == ["Cid", "Ann", "Bob", "Dee"]
    assert names(E(PEOPLE).order_by(lambda p: p.city).then_by_descending(lambda p: p.age)) == [
        "Dee", "Ann", "Cid", "Bob"
    ]
    assert E([3, 1, 2]).order().to_list() == [1, 2, 3]
    assert E([3, 1, 2]).order_descending().to_list() == [3, 2, 1]
    assert E([1, 2, 3]).reverse().to_list() == [3, 2, 1]
    assert sorted(E([1, 2, 3]).shuffle()) == [1, 2, 3]


def test_grouping_and_lookup():
    groups = E(PEOPLE).group_by(lambda p: p.city).to_list()
    assert [(g.key, names(g)) for g in groups] == [("Oslo", ["Ann", "Cid"]), ("Rome", ["Bob"]), ("Lima", ["Dee"])]
    counts = E(PEOPLE).group_by(lambda p: p.city, lambda p: p.age, result_selector=lambda k, ages: (k, ages.sum()))
    assert counts.to_list() == [("Oslo", 62), ("Rome", 25), ("Lima", 19)]
    lookup = E(PEOPLE).to_lookup(lambda p: p.city, lambda p: p.name)
    assert lookup["Oslo"].to_list() == ["Ann", "Cid"]
    assert lookup["Nowhere"].to_list() == []
    assert "Rome" in lookup and lookup.count == 3


def test_joins():
    j = E(PEOPLE).join(ORDERS, lambda p: p.name, lambda o: o.person, lambda p, o: (p.name, o.total))
    assert j.to_list() == [("Ann", 10), ("Ann", 5), ("Cid", 7)]
    gj = E(PEOPLE).group_join(ORDERS, lambda p: p.name, lambda o: o.person, lambda p, os: (p.name, os.count()))
    assert gj.to_list() == [("Ann", 2), ("Bob", 0), ("Cid", 1), ("Dee", 0)]
    lj = E(PEOPLE[:2]).left_join(ORDERS, lambda p: p.name, lambda o: o.person, lambda p, o: (p.name, o and o.total))
    assert lj.to_list() == [("Ann", 10), ("Ann", 5), ("Bob", None)]
    extra = [*ORDERS, Order(person="Eve", total=1)]
    rj = E(PEOPLE[:1]).right_join(extra, lambda p: p.name, lambda o: o.person, lambda p, o: (p and p.name, o.person))
    assert rj.to_list() == [("Ann", "Ann"), ("Ann", "Ann"), (None, "Cid"), (None, "Eve")]


def test_zip():
    assert E([1, 2, 3]).zip("ab").to_list() == [(1, "a"), (2, "b")]
    assert E([1, 2]).zip("ab", [True, False]).to_list() == [(1, "a", True), (2, "b", False)]
    assert E([1, 2]).zip_with([10, 20], lambda a, b: a + b).to_list() == [11, 22]


def test_element_operators():
    s = E([1, 2, 3])
    assert s.first() == 1 and s.first(lambda x: x > 1) == 2
    assert s.last() == 3 and s.last(lambda x: x < 3) == 2
    assert s.first_or_default(lambda x: x > 5) is None
    assert s.last_or_default(lambda x: x > 5, -1) == -1
    assert s.single(lambda x: x == 2) == 2
    assert s.single_or_default(lambda x: x > 5) is None
    assert s.element_at(1) == 2 and s.element_at(-1) == 3
    assert s.element_at_or_default(9) is None and s.element_at_or_default(-9) is None
    with pytest.raises(InvalidOperationError, match="no elements"):
        E([]).first()
    with pytest.raises(InvalidOperationError, match="no matching"):
        s.last(lambda x: x > 5)
    with pytest.raises(InvalidOperationError, match="more than one"):
        s.single()
    with pytest.raises(InvalidOperationError, match="more than one"):
        s.single_or_default(lambda x: x > 1)
    with pytest.raises(IndexError):
        s.element_at(3)


def test_quantifiers():
    s = E(PEOPLE)
    assert s.any() and not E([]).any()
    assert s.any(lambda p: p.age < 20) and s.all(lambda p: p.age > 18)
    assert s.contains(Person(name="Bob", age=25, city="Rome"))
    assert E([1, 2]).sequence_equal([1, 2]) and not E([1, 2]).sequence_equal([1, 2, 3])


def test_aggregation():
    s = E(PEOPLE)
    assert s.count() == 4 and s.count(lambda p: p.city == "Oslo") == 2 and s.long_count() == 4
    assert s.try_get_non_enumerated_count() == 4 and s.where(bool).try_get_non_enumerated_count() is None
    assert s.sum(lambda p: p.age) == 106 and E([]).sum() == 0
    assert s.average(lambda p: p.age) == 26.5
    assert s.min(lambda p: p.age) == 19 and s.max(lambda p: p.age) == 31
    assert s.min_by(lambda p: p.age).name == "Dee" and s.max_by(lambda p: p.age).name == "Ann"
    assert E([1, 2, 3]).aggregate(lambda a, b: a * b) == 6
    assert E([1, 2, 3]).aggregate(10, lambda a, b: a + b) == 16
    assert E([1, 2, 3]).aggregate(0, lambda a, b: a + b, str) == "6"
    assert s.count_by(lambda p: p.city).to_list() == [("Oslo", 2), ("Rome", 1), ("Lima", 1)]
    assert s.aggregate_by(lambda p: p.city, 0, lambda a, p: a + p.age).to_list() == [
        ("Oslo", 62), ("Rome", 25), ("Lima", 19)
    ]
    for op in (E([]).average, E([]).min, E([]).max, lambda: E([]).aggregate(max), lambda: E([]).max_by(abs)):
        with pytest.raises(InvalidOperationError):
            op()


def test_conversion():
    s = E(PEOPLE)
    assert s.to_dictionary(lambda p: p.name, lambda p: p.age) == {"Ann": 31, "Bob": 25, "Cid": 31, "Dee": 19}
    with pytest.raises(ValueError, match="same key"):
        s.to_dictionary(lambda p: p.city)
    assert E([1, 1, 2]).to_hash_set() == {1, 2}
    assert E((1, 2)).to_array() == [1, 2]


def test_enumerable_as_pydantic_field():
    class Team(BaseModel):
        members: Enumerable[Person]

    team = Team.model_validate({"members": [{"name": "Ann", "age": 31, "city": "Oslo"}]})
    assert isinstance(team.members, Enumerable)
    assert team.members.single().name == "Ann"
    assert Team(members=E(PEOPLE[:1])).members.count() == 1
    assert team.model_dump() == {"members": [{"name": "Ann", "age": 31, "city": "Oslo"}]}
    assert Team.model_validate_json(team.model_dump_json()).model_dump() == team.model_dump()
    assert Team.model_json_schema()["properties"]["members"]["type"] == "array"
    with pytest.raises(ValidationError):
        Team(members=[{"name": "x"}])
