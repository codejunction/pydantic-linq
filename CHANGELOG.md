# Changelog

All notable changes to pydantic-linq are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-10-31

### Added

- Documentation site on GitHub Pages: guides, a C# to Python operator map, and an API reference generated from the docstrings.
- This changelog.
- `pydantic_linq.orm`: Entity Framework Core for SQLModel (install `pydantic-linq[sqlmodel]`).
  - `Queryable[T]` (`IQueryable<T>`): LINQ operators that build one SQL statement. `where`, `select`, `select_many` over navigations, the sort operators, `skip`/`take`, `distinct`, the set operators, `join`/`left_join`/`right_join`, `group_by` (GROUP BY / HAVING), `count_by` and every element, quantifier and aggregate operator run in SQL. Operators SQL can't express run in memory over the results; an untranslatable `where` raises `InvalidOperationError`, as in EF Core.
  - EF query features: `include`, `then_include`, `as_no_tracking`, `as_split_query`/`as_single_query`, `tag_with`, `to_query_string`, `load`, `execute_update`, `execute_delete`, `as_enumerable`, `as_async_enumerable`.
  - Every terminal operator has a `*_async` twin (`to_list_async`, `first_async`, `count_async`, ...) for an `AsyncEngine` / `AsyncSession`.
  - `DbContext`: `set`, `add`/`add_range`, `attach`, `update`, `remove`/`remove_range`, `find`, `save_changes`, `clear`, `from_sql`, `execute_sql`, `begin_transaction`, `ensure_created`/`ensure_deleted`, and their async versions.
- Examples `08_entity_framework.py` and `09_entity_framework_async.py`.

## [0.1.0] - 2026-10-30

### Added

- `Enumerable[T]`: every `System.Linq.Enumerable` operator, including the .NET 9 and 10 ones (`index`, `count_by`, `aggregate_by`, `left_join`, `right_join`, `shuffle`, `sequence`, `infinite_sequence`). Method names are the C# names in snake_case.
- `AsyncEnumerable[T]`: the System.Linq.Async operators over sync or async iterables. A selector or predicate can be a plain function or an `async def`. Terminal operators are awaited.
- `OrderedEnumerable` / `OrderedAsyncEnumerable` with `then_by` and `then_by_descending`. The sort is stable and multi-key.
- `Grouping` / `AsyncGrouping`: a keyed sequence with every operator. `Lookup` returns an empty sequence for a missing key.
- Pydantic support:
  - `cast(Model)` validates each element with a `TypeAdapter`.
  - `Enumerable[Model]` works as a model field type, validated like `list[Model]` and serialized as a list.
  - The set operators use value equality, so they work on unhashable models.
- Importing the package adds the operators to `list`, `tuple`, `set` and `frozenset` (through forbiddenfruit). Methods the builtins already define keep their Python meaning. `uninstall()` removes the patches.
- `examples/` folder, from basics to an end-to-end async report pipeline.
- CI on Windows and Linux for Python 3.12 to 3.14. Releases publish to PyPI through trusted publishing when a tag is pushed.

[Unreleased]: https://github.com/codejunction/pydantic-linq/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/codejunction/pydantic-linq/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/codejunction/pydantic-linq/releases/tag/v0.1.0
