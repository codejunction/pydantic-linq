"""Async: AsyncEnumerable over async sources, with sync or async selectors."""

import asyncio

from pydantic import BaseModel

from pydantic_linq import AsyncEnumerable


class User(BaseModel):
    id: int
    name: str


class Profile(BaseModel):
    user_id: int
    followers: int


async def fetch_users():
    """An async generator source, e.g. a paginated API or a DB cursor."""
    for i, name in enumerate(["ann", "bob", "cid", "dee"], start=1):
        await asyncio.sleep(0.01)
        yield User(id=i, name=name)


async def fetch_profile(user: User) -> Profile:
    """An async selector, the System.Linq.Async SelectAwait overload."""
    await asyncio.sleep(0.01)
    return Profile(user_id=user.id, followers=user.id * 150)


async def is_active(user: User) -> bool:
    await asyncio.sleep(0)
    return user.id != 2


async def main() -> None:
    users = AsyncEnumerable(fetch_users())

    # Async predicate + sync projection
    names = await users.where(is_active).select(lambda u: u.name.title()).to_list()
    print("active:", names)

    # Async generator sources are one-shot (as in Python), so re-wrap for a second query
    users = AsyncEnumerable(fetch_users())
    popular = await (
        users.select(fetch_profile)
        .where(lambda p: p.followers > 200)
        .order_by_descending(lambda p: p.followers)
        .select(lambda p: p.user_id)
        .to_list()
    )
    print("popular ids:", popular)

    # A sync list enters async through AsyncEnumerable(...); terminal operators are awaited
    local = [User(id=10, name="eve"), User(id=11, name="fay")]
    print("total followers:", await AsyncEnumerable(local).select(fetch_profile).sum(lambda p: p.followers))
    print("first:", (await AsyncEnumerable(local).first(lambda u: u.id > 10)).name)

    # Grouping yields AsyncGrouping, an AsyncEnumerable with a .key
    async for g in AsyncEnumerable(fetch_users()).group_by(lambda u: u.id % 2 == 0):
        print("even" if g.key else "odd", await g.select(lambda u: u.name).to_list())


asyncio.run(main())
