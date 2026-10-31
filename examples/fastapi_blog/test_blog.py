import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["BLOG_DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/blog.db"

from blog import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_blog_api(client: TestClient):
    ann = client.post("/authors", json={"name": "Ann", "email": "ann@example.com"}).json()
    bob = client.post("/authors", json={"name": "Bob", "email": "bob@example.com"}).json()
    assert client.post("/authors", json={"name": "Ann 2", "email": "ann@example.com"}).status_code == 409
    assert client.post("/authors", json={"name": "", "email": "nope"}).status_code == 422

    def post(author, title, tags, published=True):
        body = {"title": title, "body": f"About {title}", "tags": tags, "published": published, "author_id": author["id"]}
        response = client.post("/posts", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    linq = post(ann, "LINQ in Python", ["Python", "linq", "python"])
    ef = post(ann, "EF Core over SQLModel", ["python", "orm"])
    draft = post(bob, "100% done", ["misc"], published=False)
    assert linq["tags"] == ["python", "linq"]
    assert client.post("/posts", json={"title": "x", "body": "y", "author_id": 999}).status_code == 404

    likes = [client.post(f"/posts/{ef['id']}/like").json()["likes"] for _ in range(3)]
    assert likes == [1, 2, 3]

    page = client.get("/posts", params={"tag": "python", "sort": "top"}).json()
    assert [p["title"] for p in page["items"]] == ["EF Core over SQLModel", "LINQ in Python"]
    assert page["total"] == 2
    assert client.get("/posts", params={"q": "100%"}).json()["total"] == 1  # LIKE wildcards are escaped
    assert client.get("/posts", params={"published": False}).json()["items"][0]["id"] == draft["id"]
    paged = client.get("/posts", params={"size": 2, "page": 2, "sort": "oldest"}).json()
    assert [p["id"] for p in paged["items"]] == [draft["id"]]
    assert paged["total"] == 3

    client.post(f"/posts/{linq['id']}/comments", json={"name": "Cid", "body": "Nice"})
    client.post(f"/posts/{linq['id']}/comments", json={"name": "Dee", "body": "+1"})
    detail = client.get(f"/posts/{linq['id']}").json()
    assert detail["author"]["name"] == "Ann"
    assert [c["name"] for c in detail["comments"]] == ["Cid", "Dee"]

    updated = client.patch(f"/posts/{draft['id']}", json={"published": True, "tags": ["Misc", "news"]}).json()
    assert updated["published"] is True
    assert updated["tags"] == ["misc", "news"]
    assert updated["title"] == "100% done"

    authors = client.get("/authors").json()
    assert [(a["name"], a["post_count"]) for a in authors] == [("Ann", 2), ("Bob", 1)]
    assert len(client.get(f"/authors/{ann['id']}").json()["posts"]) == 2

    stats = client.get("/stats").json()
    assert (stats["posts"], stats["likes"], stats["top_post"]["id"]) == (3, 3, ef["id"])
    assert stats["authors"][0] == {"author": "Ann", "posts": 2, "likes": 3}
    assert stats["tags"] == {"python": 2, "linq": 1, "misc": 1, "news": 1, "orm": 1}

    assert client.delete(f"/posts/{linq['id']}").status_code == 204
    assert client.get(f"/posts/{linq['id']}").status_code == 404
    assert client.get(f"/posts/{linq['id']}/comments").status_code == 404
    assert client.delete(f"/authors/{bob['id']}").status_code == 204
    assert client.get("/posts").json()["total"] == 1
    assert client.delete("/authors/999").status_code == 404
