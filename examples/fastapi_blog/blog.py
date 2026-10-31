"""A blog post API: FastAPI + SQLite, with every query written in LINQ through pydantic_linq.orm.

    pip install "pydantic-linq[sqlmodel]" "fastapi[standard]" aiosqlite
    fastapi dev examples/fastapi_blog/blog.py      # then open http://127.0.0.1:8000/docs

Set BLOG_DATABASE_URL to use another database (default: sqlite+aiosqlite:///blog.db).
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import field_validator
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, Relationship, SQLModel, col

from pydantic_linq import Enumerable
from pydantic_linq.orm import DbContext

# --- tables ---


def now() -> datetime:
    return datetime.now(UTC)


class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    bio: str = ""
    posts: list["Post"] = Relationship(back_populates="author")


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    body: str
    tags: str = ""  # stored as ",python,linq," so a tag filter is one LIKE '%,tag,%'
    published: bool = False
    likes: int = 0
    created_at: datetime = Field(default_factory=now, index=True)
    author_id: int = Field(foreign_key="author.id", index=True)
    author: Author | None = Relationship(back_populates="posts")
    comments: list["Comment"] = Relationship(back_populates="post")


class Comment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    body: str
    created_at: datetime = Field(default_factory=now)
    post_id: int = Field(foreign_key="post.id", index=True)
    post: Post | None = Relationship(back_populates="comments")


# --- request and response schemas ---


class AuthorCreate(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(regex=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    bio: str = ""


class AuthorRead(SQLModel):
    id: int
    name: str
    email: str
    bio: str


class AuthorSummary(AuthorRead):
    post_count: int


class PostCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    tags: list[str] = []
    published: bool = False
    author_id: int


class PostUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    published: bool | None = None


class PostRead(SQLModel):
    id: int
    title: str
    body: str
    tags: list[str]
    published: bool
    likes: int
    created_at: datetime
    author_id: int

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, tags: object) -> object:
        return Enumerable(tags.split(",")).where(bool).to_list() if isinstance(tags, str) else tags


class CommentCreate(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=2000)


class CommentRead(SQLModel):
    id: int
    name: str
    body: str
    created_at: datetime
    post_id: int


class PostDetail(PostRead):
    author: AuthorRead
    comments: list[CommentRead]


class AuthorDetail(AuthorRead):
    posts: list[PostRead]


class PostPage(SQLModel):
    items: list[PostRead]
    total: int
    page: int
    size: int


class AuthorStats(SQLModel):
    author: str
    posts: int
    likes: int


class Stats(SQLModel):
    posts: int
    likes: int
    top_post: PostRead | None
    authors: list[AuthorStats]
    tags: dict[str, int]


def join_tags(tags: list[str]) -> str:
    """Normalize tags (trimmed, lower case, no duplicates) and store them as ",a,b,"."""
    clean = Enumerable(tags).select(lambda t: t.strip().lower().replace(",", "")).where(bool).distinct().to_list()
    return ",".join(["", *clean, ""])


# --- app ---

engine = create_async_engine(os.environ.get("BLOG_DATABASE_URL", "sqlite+aiosqlite:///blog.db"))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with DbContext(engine) as db:
        await db.ensure_created_async()
    yield
    await engine.dispose()


app = FastAPI(title="pydantic-linq blog", lifespan=lifespan)


async def get_db() -> AsyncIterator[DbContext]:
    async with DbContext(engine) as db:
        yield db


Db = Annotated[DbContext, Depends(get_db)]


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


# --- authors ---


@app.post("/authors", response_model=AuthorRead, status_code=status.HTTP_201_CREATED)
async def create_author(data: AuthorCreate, db: Db) -> Author:
    if await db.set(Author).any_async(lambda a: a.email == data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    author = Author.model_validate(data)
    db.add(author)
    await db.save_changes_async()
    return author


@app.get("/authors", response_model=list[AuthorSummary])
async def list_authors(db: Db) -> list[AuthorSummary]:
    # GROUP BY author_id, COUNT(*) in SQL; as_async_enumerable() continues in memory over the fetched authors.
    counts: dict[int | None, int] = await db.set(Post).count_by(lambda p: p.author_id).to_dictionary_async(lambda kv: kv[0], lambda kv: kv[1])
    return await (
        db.set(Author)
        .order_by(lambda a: a.name)
        .as_async_enumerable()
        .select(lambda a: AuthorSummary(**a.model_dump(), post_count=counts.get(a.id, 0)))
        .to_list()
    )


@app.get("/authors/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: int, db: Db) -> Author:
    author = await db.set(Author).include(lambda a: a.posts).first_or_default_async(lambda a: a.id == author_id)
    if author is None:
        raise not_found("author")
    return author


@app.delete("/authors/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_author(author_id: int, db: Db) -> None:
    post_ids = await db.set(Post).where(lambda p: p.author_id == author_id).select(lambda p: p.id).to_list_async()
    await db.set(Comment).where(lambda c: col(c.post_id).in_(post_ids)).execute_delete_async()
    await db.set(Post).where(lambda p: p.author_id == author_id).execute_delete_async()
    if not await db.set(Author).where(lambda a: a.id == author_id).execute_delete_async():
        raise not_found("author")
    await db.save_changes_async()


# --- posts ---


@app.get("/posts", response_model=PostPage)
async def list_posts(
    db: Db,
    q: str | None = None,
    tag: str | None = None,
    author_id: int | None = None,
    published: bool | None = None,
    sort: Literal["newest", "oldest", "top"] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PostPage:
    posts = db.set(Post)
    if q:
        posts = posts.where(lambda p: col(p.title).contains(q, autoescape=True) | col(p.body).contains(q, autoescape=True))
    if tag:
        posts = posts.where(lambda p: col(p.tags).contains(f",{tag.lower()},", autoescape=True))
    if author_id is not None:
        posts = posts.where(lambda p: p.author_id == author_id)
    if published is not None:
        posts = posts.where(lambda p: p.published == published)

    ordered = {
        "newest": posts.order_by_descending(lambda p: p.created_at),
        "oldest": posts.order_by(lambda p: p.created_at),
        "top": posts.order_by_descending(lambda p: p.likes),
    }[sort].then_by_descending(lambda p: p.id)
    items = await ordered.skip((page - 1) * size).take(size).as_async_enumerable().select(PostRead.model_validate).to_list()
    return PostPage(items=items, total=await posts.count_async(), page=page, size=size)


@app.post("/posts", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(data: PostCreate, db: Db) -> Post:
    if await db.find_async(Author, data.author_id) is None:
        raise not_found("author")
    post = Post.model_validate(data, update={"tags": join_tags(data.tags)})
    db.add(post)
    await db.save_changes_async()
    return post


@app.get("/posts/{post_id}", response_model=PostDetail)
async def get_post(post_id: int, db: Db) -> Post:
    post = await (
        db.set(Post)
        .include(lambda p: p.author)
        .include(lambda p: p.comments)
        .as_no_tracking()
        .first_or_default_async(lambda p: p.id == post_id)
    )
    if post is None:
        raise not_found("post")
    return post


@app.patch("/posts/{post_id}", response_model=PostRead)
async def update_post(post_id: int, data: PostUpdate, db: Db) -> Post:
    post = await db.find_async(Post, post_id)
    if post is None:
        raise not_found("post")
    changes = data.model_dump(exclude_unset=True)
    if "tags" in changes:
        changes["tags"] = join_tags(changes["tags"] or [])
    post.sqlmodel_update(changes)
    await db.save_changes_async()
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Db) -> None:
    await db.set(Comment).where(lambda c: c.post_id == post_id).execute_delete_async()
    if not await db.set(Post).where(lambda p: p.id == post_id).execute_delete_async():
        raise not_found("post")
    await db.save_changes_async()


@app.post("/posts/{post_id}/like")
async def like_post(post_id: int, db: Db) -> dict[str, int]:
    # ExecuteUpdate: one UPDATE post SET likes = likes + 1, so concurrent likes don't race.
    post = db.set(Post).where(lambda p: p.id == post_id)
    if not await post.execute_update_async(lambda p: {p.likes: p.likes + 1}):
        raise not_found("post")
    await db.save_changes_async()
    return {"likes": await post.select(lambda p: p.likes).first_async()}


# --- comments ---


@app.get("/posts/{post_id}/comments", response_model=list[CommentRead])
async def list_comments(post_id: int, db: Db) -> list[Comment]:
    if not await db.set(Post).any_async(lambda p: p.id == post_id):
        raise not_found("post")
    return await db.set(Comment).where(lambda c: c.post_id == post_id).order_by(lambda c: c.created_at).to_list_async()


@app.post("/posts/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(post_id: int, data: CommentCreate, db: Db) -> Comment:
    if not await db.set(Post).any_async(lambda p: p.id == post_id):
        raise not_found("post")
    comment = Comment.model_validate(data, update={"post_id": post_id})
    db.add(comment)
    await db.save_changes_async()
    return comment


@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: Db) -> None:
    if not await db.set(Comment).where(lambda c: c.id == comment_id).execute_delete_async():
        raise not_found("comment")
    await db.save_changes_async()


# --- stats ---


@app.get("/stats", response_model=Stats)
async def stats(db: Db) -> Stats:
    posts = db.set(Post)
    names = await db.set(Author).select(lambda a: (a.id, a.name)).to_dictionary_async(lambda r: r[0], lambda r: r[1])
    # GROUP BY author_id with COUNT and SUM in SQL.
    per_author = await (
        posts.group_by(lambda p: p.author_id)
        .select(lambda g: (g.key, g.count(), g.sum(lambda p: p.likes)))
        .order_by_descending(lambda r: r[2])
        .as_async_enumerable()
        .select(lambda r: AuthorStats(author=names[r[0]], posts=r[1], likes=r[2]))
        .to_list()
    )
    # Tag counts: SQL fetches the tag column, then LINQ splits and counts the tags in memory.
    tags = await (
        posts.select(lambda p: p.tags)
        .as_async_enumerable()
        .select_many(lambda s: s.split(","))
        .where(bool)
        .count_by(lambda t: t)
        .order_by_descending(lambda kv: kv[1])
        .then_by(lambda kv: kv[0])
        .take(10)
        .to_dictionary(lambda kv: kv[0], lambda kv: kv[1])
    )
    top = await posts.order_by_descending(lambda p: p.likes).first_or_default_async()
    return Stats(
        posts=await posts.count_async(),
        likes=await posts.sum_async(lambda p: p.likes),
        top_post=top and PostRead.model_validate(top),
        authors=per_author,
        tags=tags,
    )
