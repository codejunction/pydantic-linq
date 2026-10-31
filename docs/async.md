# Async

`AsyncEnumerable[T]` is the port of System.Linq.Async (`IAsyncEnumerable<T>`).

```python
import asyncio
from pydantic_linq import AsyncEnumerable

async def fetch_users():          # any async iterable: an async generator, a DB cursor, ...
    for i in range(5):
        await asyncio.sleep(0)
        yield i

async def score(user_id: int) -> int:
    await asyncio.sleep(0)
    return user_id * 10

async def main():
    top = await (
        AsyncEnumerable(fetch_users())
        .where(lambda u: u > 0)       # sync predicate
        .select(score)                # async selector
        .order_by_descending(lambda s: s)
        .take(2)
        .to_list()
    )
    print(top)  # [40, 30]

asyncio.run(main())
```

## Rules

- **Sources.** Pass any `AsyncIterable` or plain `Iterable`. From an `Enumerable` you can also call `.to_async_enumerable()`.
- **Sync or async callables.** Every selector, predicate, key and result selector can be a plain function or return an awaitable. That covers both the System.Linq.Async `*Await` overloads (`SelectAwait`, `WhereAwait`, ...) and the .NET 10 `AsyncEnumerable` overloads, with one method each.
- **Terminal operators are awaited.** `await q.to_list()`, `await q.first()`, `await q.count()`, and so on. The names drop the C# `Async` suffix (`ToListAsync` becomes `to_list`).
- **Sequence operators are deferred**, as in the sync version. Iterate them with `async for`.
- **Grouping.** `group_by` yields `AsyncGrouping`, an `AsyncEnumerable` with a `.key`. `await to_lookup(...)` returns the sync `Lookup`, like `ToLookupAsync`.

!!! warning "One-shot sources"
    An async generator can only be iterated once, as in Python itself. To run two queries over it, create a new generator for each. Collections such as lists can be enumerated any number of times.
