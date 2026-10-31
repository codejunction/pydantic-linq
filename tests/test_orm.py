import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, Relationship, SQLModel, col, create_engine

from pydantic_linq import InvalidOperationError
from pydantic_linq.orm import DbContext


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    heroes: list["Hero"] = Relationship(back_populates="team")


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    age: int
    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="heroes")


def seed(db: DbContext) -> None:
    avengers, xmen = Team(name="Avengers"), Team(name="X-Men")
    db.add_range(
        [
            Hero(name="Tony", age=48, team=avengers),
            Hero(name="Steve", age=100, team=avengers),
            Hero(name="Logan", age=150, team=xmen),
            Hero(name="Jean", age=30, team=xmen),
            Hero(name="Peter", age=18),
        ]
    )
    db.add(Team(name="Empty"))


@pytest.fixture
def db():
    with DbContext(create_engine("sqlite://")) as db:
        db.ensure_created()
        seed(db)
        db.save_changes()
        yield db


def names(q) -> list[str]:
    return q.select(lambda h: h.name).to_list()


def test_where_order_select(db):
    heroes = db.set(Hero)
    assert names(heroes.where(lambda h: h.age > 40).order_by(lambda h: h.name)) == ["Logan", "Steve", "Tony"]
    assert heroes.where(lambda h: (h.age < 20) | col(h.name).in_(["Jean"])).count() == 2
    assert heroes.order_by_descending(lambda h: h.team_id).then_by(lambda h: h.age).select(
        lambda h: (h.name, h.age)
    ).take(2).to_list() == [("Jean", 30), ("Logan", 150)]
    # where after select filters the projected column
    assert heroes.select(lambda h: h.name).where(lambda n: n.startswith("T")).to_list() == ["Tony"]
    assert "WHERE hero.age > 40" in heroes.where(lambda h: h.age > 40).to_query_string()


def test_untranslatable_where_raises_but_select_runs_in_memory(db):
    with pytest.raises(InvalidOperationError):
        db.set(Hero).where(lambda h: h.age > 1 and h.age < 99)
    shouted = db.set(Hero).order_by(lambda h: h.age).select(lambda h: h.name.upper()).take(2).to_list()
    assert shouted == ["PETER", "JEAN"]
    assert db.set(Hero).select(lambda h: {"n": h.name}).where(lambda d: d["n"] == "Tony").count() == 1


def test_paging_matches_linq(db):
    by_age = db.set(Hero).order_by(lambda h: h.age)
    assert names(by_age.take(4).skip(1)) == ["Jean", "Tony", "Steve"]
    assert names(by_age.take(slice(1, 3))) == ["Jean", "Tony"]
    # where after take filters the paged rows (a subquery), as in LINQ
    assert by_age.take(3).where(lambda h: h.age > 20).count() == 2
    assert by_age.skip(10).to_list() == []
    assert names(by_age.reverse().take(1)) == ["Logan"]


def test_element_operators(db):
    heroes = db.set(Hero)
    assert heroes.first(lambda h: h.name == "Logan").age == 150
    assert heroes.first_or_default(lambda h: h.age > 999) is None
    with pytest.raises(InvalidOperationError):
        heroes.single(lambda h: h.age > 40)
    assert heroes.single(lambda h: h.name == "Jean").age == 30
    assert heroes.order_by(lambda h: h.age).last().name == "Logan"
    with pytest.raises(InvalidOperationError):
        heroes.last()  # no order, as EF Core
    assert heroes.order_by(lambda h: h.age).element_at(1).name == "Jean"
    assert heroes.order_by(lambda h: h.age).element_at(-1).name == "Logan"
    with pytest.raises(IndexError):
        heroes.element_at(99)
    assert heroes.min_by(lambda h: h.age).name == "Peter"
    assert heroes.max_by(lambda h: h.age).name == "Logan"


def test_aggregates_and_quantifiers(db):
    heroes = db.set(Hero)
    assert heroes.any(lambda h: h.age > 120) and heroes.all(lambda h: h.age > 10)
    assert not heroes.all(lambda h: h.age > 20)
    assert heroes.sum(lambda h: h.age) == 346
    assert (heroes.min(lambda h: h.age), heroes.max(lambda h: h.age)) == (18, 150)
    assert heroes.select(lambda h: h.age).average() == 346 / 5
    assert heroes.select(lambda h: h.team_id).distinct().count() == 3
    assert heroes.where(lambda h: h.age > 999).sum(lambda h: h.age) == 0
    with pytest.raises(InvalidOperationError):
        heroes.where(lambda h: h.age > 999).max(lambda h: h.age)
    tony = heroes.first(lambda h: h.name == "Tony")
    assert heroes.contains(tony) and heroes.select(lambda h: h.name).contains("Jean")


def test_group_by_translates_to_group_by_having(db):
    q = (
        db.set(Hero)
        .group_by(lambda h: h.team_id)
        .where(lambda g: g.count() > 1)
        .order_by(lambda g: g.key)
        .select(lambda g: (g.key, g.count(), g.sum(lambda h: h.age), g.max(lambda h: h.age)))
    )
    assert "GROUP BY" in q.to_query_string() and "HAVING" in q.to_query_string()
    assert q.to_list() == [(1, 2, 148, 100), (2, 2, 180, 150)]
    assert db.set(Hero).count_by(lambda h: h.team_id).where(lambda kv: kv[1] == 1).to_list() == [(None, 1)]
    assert db.set(Hero).group_by(lambda h: h.team_id).count() == 3
    # enumerated directly, groups are built in memory
    groups = {g.key: g.select(lambda h: h.name).to_list() for g in db.set(Hero).group_by(lambda h: h.team_id)}
    assert groups[1] == ["Tony", "Steve"]
    # a select SQL can't express groups in memory with the same lambda
    assert db.set(Hero).group_by(lambda h: h.team_id).select(lambda g: {g.key: g.count()}).to_list()[0] == {1: 2}


def test_joins(db):
    pairs = (
        db.set(Hero)
        .join(db.set(Team), lambda h: h.team_id, lambda t: t.id, lambda h, t: (h.name, t.name))
        .order_by(lambda p: p[0])
        .to_list()
    )
    assert pairs[0] == ("Jean", "X-Men") and len(pairs) == 4
    left = db.set(Hero).left_join(db.set(Team), lambda h: h.team_id, lambda t: t.id, lambda h, t: (h.name, t.name))
    assert ("Peter", None) in left.to_list()
    right = db.set(Hero).right_join(db.set(Team), lambda h: h.team_id, lambda t: t.id, lambda h, t: (h.name, t.name))
    assert (None, "Empty") in right.to_list()
    entities = db.set(Hero).join(db.set(Team), lambda h: h.team_id, lambda t: t.id, lambda h, t: (h, t)).to_list()
    assert all(h.team is t for h, t in entities)
    # select_many over a collection navigation is a join
    assert sorted(names(db.set(Team).select_many(lambda t: t.heroes))) == ["Jean", "Logan", "Steve", "Tony"]


def test_set_operations(db):
    young = db.set(Hero).where(lambda h: h.age < 50)
    avengers = db.set(Hero).where(lambda h: h.team_id == 1)
    assert sorted(names(young.union(avengers))) == ["Jean", "Peter", "Steve", "Tony"]
    assert names(young.intersect(avengers)) == ["Tony"]
    assert sorted(names(young.except_(avengers))) == ["Jean", "Peter"]
    assert young.concat(avengers).count() == 5
    assert young.union(avengers).where(lambda h: h.age > 40).count() == 2


def test_include_then_include_no_tracking(db):
    heroes = (
        db.set(Hero)
        .include(lambda h: h.team)
        .then_include(lambda t: t.heroes)
        .where(lambda h: col(h.team_id).is_not(None))
        .as_no_tracking()
        .to_list()
    )
    db.clear()
    assert {h.team.name for h in heroes if h.team} == {"Avengers", "X-Men"}
    assert all(len(h.team.heroes) == 2 for h in heroes if h.team)
    single = db.set(Hero).include(lambda h: h.team).as_single_query().where(lambda h: h.name == "Tony")
    assert "JOIN" in single.to_query_string() and single.single().team.name == "Avengers"


def test_in_memory_fallback_and_tags(db):
    heroes = db.set(Hero).order_by(lambda h: h.age)
    assert heroes.zip_with(heroes.skip(1), lambda a, b: b.age - a.age).to_list() == [12, 18, 52, 50]
    assert heroes.as_enumerable().chunk(2).count() == 3
    assert db.set(Hero).tag_with("report").to_query_string().startswith("SELECT /* report */")


def test_changes_bulk_and_raw_sql(db):
    tony = db.set(Hero).single(lambda h: h.name == "Tony")
    tony.age = 49
    db.remove(db.set(Hero).first(lambda h: h.name == "Peter"))
    assert db.save_changes() == 2
    assert db.find(Hero, tony.id) is tony
    assert db.set(Hero).where(lambda h: h.age > 100).execute_update(lambda h: {h.age: h.age + 1}) == 1
    assert db.set(Hero).order_by(lambda h: h.age).take(1).execute_delete() == 1  # Jean
    db.save_changes()
    assert sorted(names(db.set(Hero))) == ["Logan", "Steve", "Tony"]
    old = db.from_sql(Hero, "SELECT * FROM hero WHERE age > :age", age=99).order_by(lambda h: h.age)
    assert names(old) == ["Steve", "Logan"]
    assert old.select(lambda h: h.age).last() == 151  # tracked Logan is stale after execute_update, as in EF
    with db.begin_transaction() as tx:
        db.execute_sql("DELETE FROM hero")
        tx.rollback()
    assert db.set(Hero).count() == 3


def test_async():
    async def main():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with DbContext(engine) as db:
            await db.ensure_created_async()
            seed(db)
            assert await db.save_changes_async() == 8
            heroes = db.set(Hero)
            assert await heroes.where(lambda h: h.age > 40).count_async() == 3
            assert (await heroes.order_by(lambda h: h.age).first_async()).name == "Peter"
            assert await heroes.select(lambda h: h.name).order().to_list_async() == sorted(
                ["Tony", "Steve", "Logan", "Jean", "Peter"]
            )
            assert await heroes.sum_async(lambda h: h.age) == 346
            stats = await heroes.count_by(lambda h: h.team_id).to_dictionary_async(lambda kv: kv[0], lambda kv: kv[1])
            assert stats == {None: 1, 1: 2, 2: 2}
            loaded = await heroes.include(lambda h: h.team).where(lambda h: h.name == "Tony").single_async()
            assert loaded.team and loaded.team.name == "Avengers"
            seen: list[str] = []

            async def visit(h):
                seen.append(h.name)

            await heroes.where(lambda h: h.age < 40).for_each_async(visit)
            assert sorted(seen) == ["Jean", "Peter"]
            assert await heroes.as_async_enumerable().select(lambda h: h.age).max() == 150
            assert await heroes.where(lambda h: h.age < 20).execute_delete_async() == 1
            assert (await db.find_async(Hero, loaded.id)) is loaded
            with pytest.raises(InvalidOperationError):
                heroes.to_list()
        await engine.dispose()

    asyncio.run(main())
