"""C# LINQ for Python, typed and Pydantic-aware.

Layers (each depends only on the ones above it):
    core/          errors, value-equality set, grouping and sorting helpers
    sync/          Enumerable: operators/ (one mixin per LINQ category) composed in enumerable.py
    aio/           AsyncEnumerable: same layout, sync-or-async selectors, awaitable terminal operators
    integrations/  pydantic field support
    orm/           Entity Framework over SQLModel (optional extra, import pydantic_linq.orm)

Wrap any iterable to query it: Enumerable(rows).where(...).to_list().
"""

from .aio.enumerable import AsyncEnumerable
from .aio.grouping import AsyncGrouping
from .aio.ordered import OrderedAsyncEnumerable
from .core import InvalidOperationError
from .sync.enumerable import Enumerable
from .sync.grouping import Grouping, Lookup
from .sync.ordered import OrderedEnumerable

__all__ = [
    "AsyncEnumerable",
    "AsyncGrouping",
    "Enumerable",
    "Grouping",
    "InvalidOperationError",
    "Lookup",
    "OrderedAsyncEnumerable",
    "OrderedEnumerable",
]
