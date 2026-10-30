# pydantic-linq

C# LINQ (System.Linq + System.Linq.Async) for Python, typed and Pydantic-aware. Published to PyPI as `pydantic-linq`.

## Thumb rule: every code change updates the changelog and the docs

Any change under `src/` or `examples/` (a new operator, a behavior change, a bug fix, a rename) is not done until:

1. **`CHANGELOG.md`** has an entry under `## [Unreleased]`, in the matching Keep a Changelog section: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` or `Security`. Write one line per change, from the user's point of view.
2. **`docs/`** reflects the change:
   - a new or renamed operator: update `docs/operators.md`;
   - a behavior or convention change: update the guide page it affects (`getting-started`, `async`, `pydantic` or `builtins`);
   - a new example: add it to `docs/examples.md`.

   The API reference (`docs/api/`) is generated from the docstrings, so keep the docstrings accurate.
3. **`README.md`** is updated when the change touches anything it shows: the quick start, conventions, install or layout.
4. **`uv run --group docs mkdocs build --strict`** passes.

Pure refactors and test-only changes need no changelog entry.

## Layout

Each layer depends only on the layers listed above it:

- `src/pydantic_linq/core/`: errors, the value-equality set, group and sort helpers. No internal dependencies.
- `src/pydantic_linq/sync/`: `Enumerable`. `operators/` has one mixin per LINQ category, combined in `enumerable.py`.
- `src/pydantic_linq/aio/`: `AsyncEnumerable`, with the same layout.
- `src/pydantic_linq/integrations/`: the pydantic field schema and the builtin patching (forbiddenfruit).

A new operator goes in the mixin for its category, in both `sync/operators/` and `aio/operators/`.

## Checks

```bash
uv run pytest -q
uvx ruff check
uvx pyright src
for f in examples/*.py; do uv run python "$f" > /dev/null; done
uv run --group docs mkdocs build --strict
```

## Release

1. Bump `version` in `pyproject.toml`.
2. In `CHANGELOG.md`, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, add an empty `[Unreleased]` above it, and update the compare links at the bottom.
3. Commit, then `git tag vX.Y.Z && git push origin vX.Y.Z`.

`release.yml` then runs CI, builds the package, publishes to PyPI (trusted publisher, environment `pypi`) and creates the GitHub release. `pages.yml` redeploys the docs on every push to `main` that touches docs or code.
