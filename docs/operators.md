# Operator map (C# to Python)

Every `System.Linq.Enumerable` operator and its pydantic-linq name. `AsyncEnumerable` has the same names. There, the terminal operators (the ones that return a value, not a sequence) are awaited.

## General conventions

| C# | Python |
|---|---|
| `PascalCase` method | `snake_case` method |
| `Func<T, TResult>` | `Callable[[T], R]`, or an `async def` in `AsyncEnumerable` |
| Overload with an index (`Select((x, i) => ...)`) | `.index()` (yields `(i, x)`), then the operator |
| `IComparer<T>` | `cmp(a, b) -> int` |
| `KeyValuePair<K, V>` | `(key, value)` tuple |
| `Index` (`^1`) | negative int |
| `Range` (`1..^1`) | `slice(1, -1)` |
| `T[]` | `list[T]` |
| `Except` | `except_` (`except` is a Python keyword) |

## Operators

| Category | C# | Python |
|---|---|---|
| Generation | `Empty`, `Range`, `Repeat` | `Enumerable.empty()`, `Enumerable.range(start, count)`, `Enumerable.repeat(x, count)` |
| | `Sequence`, `InfiniteSequence` (.NET 10) | `Enumerable.sequence(start, end_inclusive, step)`, `Enumerable.infinite_sequence(start, step)` |
| | `DefaultIfEmpty` | `default_if_empty(default=None)` |
| Filtering | `Where`, `OfType<T>` | `where(pred)`, `of_type(T)` |
| Projection | `Select`, `SelectMany` | `select(f)`, `select_many(f[, result_selector])` |
| | `Index` (.NET 9) | `index()` |
| | `Zip` | `zip(second[, third])` gives tuples; `zip_with(second, f)` |
| Partitioning | `Take`, `Skip` | `take(n)` or `take(slice)`, `skip(n)` |
| | `TakeWhile`, `SkipWhile` | `take_while(pred)`, `skip_while(pred)` |
| | `TakeLast`, `SkipLast` | `take_last(n)`, `skip_last(n)` |
| | `Chunk` | `chunk(size)` gives lists |
| Concatenation | `Concat`, `Append`, `Prepend` | `concat`, `append`, `prepend` |
| Sets | `Distinct`, `DistinctBy` | `distinct()`, `distinct_by(key)` |
| | `Union`, `UnionBy` | `union(second)`, `union_by(second, key)` |
| | `Intersect`, `IntersectBy` | `intersect(second)`, `intersect_by(keys, key)` |
| | `Except`, `ExceptBy` | `except_(second)`, `except_by(keys, key)` |
| Sorting | `OrderBy`, `OrderByDescending` | `order_by(key[, cmp])`, `order_by_descending(key[, cmp])` |
| | `Order`, `OrderDescending` | `order([cmp])`, `order_descending([cmp])` |
| | `ThenBy`, `ThenByDescending` | `then_by(key[, cmp])`, `then_by_descending(key[, cmp])` |
| | `Reverse`, `Shuffle` (.NET 10) | `reverse()`, `shuffle()` |
| Grouping | `GroupBy` | `group_by(key[, element][, result_selector=])` |
| | `ToLookup` | `to_lookup(key[, element])` |
| Joining | `Join`, `GroupJoin` | `join(inner, outer_key, inner_key, f)`, `group_join(...)` |
| | `LeftJoin`, `RightJoin` (.NET 10) | `left_join(...)`, `right_join(...)`; the missing side is `None` |
| Element | `First`, `FirstOrDefault` | `first([pred])`, `first_or_default([pred][, default])` |
| | `Last`, `LastOrDefault` | `last([pred])`, `last_or_default([pred][, default])` |
| | `Single`, `SingleOrDefault` | `single([pred])`, `single_or_default([pred][, default])` |
| | `ElementAt`, `ElementAtOrDefault` | `element_at(i)`, `element_at_or_default(i[, default])` |
| Quantifiers | `Any`, `All`, `Contains` | `any([pred])`, `all(pred)`, `contains(x)` |
| Equality | `SequenceEqual` | `sequence_equal(second)` |
| Aggregation | `Count`, `LongCount` | `count([pred])`, `long_count([pred])` |
| | `TryGetNonEnumeratedCount` | `try_get_non_enumerated_count()` gives `int` or `None` |
| | `Sum`, `Average`, `Min`, `Max` | `sum([f])`, `average([f])`, `min([f])`, `max([f])` |
| | `MinBy`, `MaxBy` | `min_by(key)`, `max_by(key)` |
| | `Aggregate` | `aggregate(func)`, `aggregate(seed, func[, result_selector])` |
| | `CountBy`, `AggregateBy` (.NET 9) | `count_by(key)`, `aggregate_by(key, seed, func)` |
| Conversion | `AsEnumerable`, `Cast<T>` | `as_enumerable()`, `cast(T[, strict=])`, which validates with pydantic |
| | `ToList`, `ToArray`, `ToHashSet` | `to_list()`, `to_array()`, `to_hash_set()` |
| | `ToDictionary` | `to_dictionary(key[, element])` |
| | `ToAsyncEnumerable` | `to_async_enumerable()` |

## Not ported

- **`IEqualityComparer<T>` arguments.** Use the `*_by` variants with a key function, or define `__eq__`/`__hash__` (or `frozen=True`) on the model.
- **`LongCount` returning `long`.** Python ints don't overflow, so it is the same as `count`.
