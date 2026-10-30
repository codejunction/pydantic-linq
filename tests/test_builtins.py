from pydantic import BaseModel

import pydantic_linq
from pydantic_linq import Enumerable


class Row(BaseModel):
    id: int
    tag: str


ROWS = [Row(id=1, tag="a"), Row(id=2, tag="b"), Row(id=3, tag="a")]


def test_list_of_models_gets_linq_on_import():
    assert ROWS.where(lambda r: r.tag == "a").select(lambda r: r.id).to_list() == [1, 3]
    assert ROWS.first(lambda r: r.id > 1).id == 2
    assert ROWS.group_by(lambda r: r.tag).select(lambda g: (g.key, len(g))).to_list() == [("a", 2), ("b", 1)]
    assert isinstance(ROWS.select(lambda r: r.id), Enumerable)


def test_tuple_set_frozenset():
    assert (3, 1, 2).order().to_list() == [1, 2, 3]
    assert {1, 2}.sum() == 3
    assert frozenset({5}).single() == 5


def test_builtin_names_keep_python_meaning():
    assert [1, 1, 2].count(1) == 2
    assert [1, 1, 2].as_enumerable().count() == 3
    assert {1}.union({2}) == {1, 2}


def test_uninstall_and_reinstall():
    pydantic_linq.uninstall()
    try:
        assert not hasattr([], "select")
    finally:
        pydantic_linq.install()
    assert [1].select(str).to_list() == ["1"]
