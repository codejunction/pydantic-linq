"""Entity Framework style queries over SQLModel: LINQ that runs as SQL.

Needs the extra: pip install pydantic-linq[sqlmodel]
"""

from sqlmodel import Field, Relationship, SQLModel, col, create_engine

from pydantic_linq.orm import DbContext


class Blog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    posts: list["Post"] = Relationship(back_populates="blog")


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    likes: int
    blog_id: int | None = Field(default=None, foreign_key="blog.id")
    blog: Blog | None = Relationship(back_populates="posts")


with DbContext(create_engine("sqlite://")) as db:
    db.ensure_created()

    # Add / SaveChanges
    python, dotnet = Blog(name="Python"), Blog(name=".NET")
    db.add_range(
        [
            Post(title="Generics in 3.12", likes=120, blog=python),
            Post(title="Pattern matching", likes=80, blog=python),
            Post(title="LINQ deep dive", likes=300, blog=dotnet),
            Post(title="EF Core 10", likes=210, blog=dotnet),
            Post(title="Records", likes=40, blog=dotnet),
        ]
    )
    print("saved:", db.save_changes())

    posts = db.set(Post)  # DbSet<Post>

    # Lambdas build SQL: use & | ~ for and / or / not.
    popular = posts.where(lambda p: (p.likes > 100) & ~col(p.title).contains("3.12")).order_by_descending(lambda p: p.likes)
    print(popular.to_query_string())
    print("popular:", popular.select(lambda p: p.title).to_list())

    # Paging, element operators and aggregates are SQL too.
    print("page 2:", posts.order_by(lambda p: p.id).skip(2).take(2).select(lambda p: p.title).to_list())
    print("top:", posts.max_by(lambda p: p.likes).title, "| total likes:", posts.sum(lambda p: p.likes))

    # GroupBy + Select -> GROUP BY / HAVING
    per_blog = (
        posts.group_by(lambda p: p.blog_id)
        .where(lambda g: g.count() > 1)
        .select(lambda g: (g.key, g.count(), g.average(lambda p: p.likes)))
    )
    print("per blog:", per_blog.to_list())

    # Join -> INNER JOIN; the result selector picks columns.
    titles = posts.join(db.set(Blog), lambda p: p.blog_id, lambda b: b.id, lambda p, b: (b.name, p.title))
    print("joined:", titles.order_by(lambda t: t[1]).take(3).to_list())

    # Include / ThenInclude load relationships eagerly.
    for blog in db.set(Blog).include(lambda b: b.posts).order_by(lambda b: b.name):
        print(blog.name, [p.title for p in blog.posts])

    # A select SQL can't express runs in memory on the fetched rows (EF client projection).
    print(posts.order_by(lambda p: p.likes).select(lambda p: f"{p.title} ({p.likes})").first())

    # Tracked changes, ExecuteUpdate / ExecuteDelete, raw SQL.
    records = posts.single(lambda p: p.title == "Records")
    records.likes += 1
    db.save_changes()
    print("bumped:", posts.where(lambda p: p.likes < 100).execute_update(lambda p: {p.likes: p.likes + 10}))
    print("deleted:", posts.where(lambda p: p.likes < 60).execute_delete())
    db.save_changes()
    print("raw:", db.from_sql(Post, "SELECT * FROM post WHERE likes > :n", n=200).count())
