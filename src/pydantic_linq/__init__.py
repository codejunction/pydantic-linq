"""C# LINQ for Python, typed and Pydantic-aware.

Layers (each depends only on the ones above it):
    core/          errors, value-equality set, grouping and sorting helpers
    sync/          Enumerable: operators/ (one mixin per LINQ category) composed in enumerable.py
    aio/           AsyncEnumerable: same layout, sync-or-async selectors, awaitable terminal operators
    integrations/  pydantic field support, builtin list/tuple/set patching

Importing the package patches list, tuple, set and frozenset with the LINQ operators.
"""

from .aio.enumerable import AsyncEnumerable
from .aio.grouping import AsyncGrouping
from .aio.ordered import OrderedAsyncEnumerable
from .core import InvalidOperationError
from .integrations.builtins import install, uninstall
from .sync.enumerable import Enumerable
from .sync.grouping import Grouping, Lookup
from .sync.ordered import OrderedEnumerable

install()

__all__ = [
    "AsyncEnumerable",
    "AsyncGrouping",
    "Enumerable",
    "Grouping",
    "InvalidOperationError",
    "Lookup",
    "OrderedAsyncEnumerable",
    "OrderedEnumerable",
    "install",
    "uninstall",
]
