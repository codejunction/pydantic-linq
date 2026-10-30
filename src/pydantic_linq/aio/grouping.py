from __future__ import annotations

from .enumerable import AsyncEnumerable


class AsyncGrouping[K, T](AsyncEnumerable[T]):
    """IAsyncGrouping<TKey, TElement>: a keyed AsyncEnumerable."""

    __slots__ = ("key",)

    def __init__(self, key: K, items: list[T]) -> None:
        super().__init__(items)
        self.key = key

    def __len__(self) -> int:
        return len(self._source)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return f"AsyncGrouping({self.key!r}, {self._source!r})"
