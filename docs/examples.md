# Examples

These are the runnable scripts in [`examples/`](https://github.com/codejunction/pydantic-linq/tree/main/examples), from simple to complex. CI runs every one of them.

## 01 Basics

```python
--8<-- "examples/01_basics.py"
```

## 02 Sorting and paging

```python
--8<-- "examples/02_sorting_paging.py"
```

## 03 Grouping and aggregation

```python
--8<-- "examples/03_grouping_aggregation.py"
```

## 04 Joins and sets

```python
--8<-- "examples/04_joins_sets.py"
```

## 05 Pydantic integration

```python
--8<-- "examples/05_pydantic_integration.py"
```

## 06 Async

```python
--8<-- "examples/06_async.py"
```

## 07 End-to-end sales report

```python
--8<-- "examples/07_sales_report.py"
```

## 08 Entity Framework (SQLModel)

```python
--8<-- "examples/08_entity_framework.py"
```

## 09 Entity Framework, async

```python
--8<-- "examples/09_entity_framework_async.py"
```

## FastAPI blog API

[`examples/fastapi_blog/`](https://github.com/codejunction/pydantic-linq/tree/main/examples/fastapi_blog) is a complete async REST API over SQLite: authors, posts and comments, with search, tag filters, sorting, paging and stats. Every query is LINQ through `pydantic_linq.orm`. `test_blog.py` drives it end to end and runs with the test suite.

```bash
pip install "pydantic-linq[sqlmodel]" "fastapi[standard]" aiosqlite
fastapi dev examples/fastapi_blog/blog.py   # open http://127.0.0.1:8000/docs
```

```python
--8<-- "examples/fastapi_blog/blog.py"
```
