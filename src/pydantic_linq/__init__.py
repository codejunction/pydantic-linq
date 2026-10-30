"""C# LINQ for Python, typed and Pydantic-aware.

Layers (each depends only on the ones above it):
    core/          errors, value-equality set, Grouping
    sync/          Enumerable: operators/ (one mixin per LINQ category) composed in enumerable.py
    aio/           AsyncEnumerable: same layout, sync-or-async selectors, awaitable terminal operators
    integrations/  pydantic field support, builtin list/tuple/set patching

Importing the package patches list, tuple, set and frozenset with the LINQ operators.
"""

from .aio.enumerable import AsyncEnumerable
from .aio.ordered import OrderedAsyncEnumerable
from .core import Grouping, InvalidOperationError
from .integrations.builtins import install, uninstall
from .sync.enumerable import Enumerable
from .sync.lookup import Lookup
from .sync.ordered import OrderedEnumerable

install()

__all__ = [
    "AsyncEnumerable",
    "Enumerable",
    "Grouping",
    "InvalidOperationError",
    "Lookup",
    "OrderedAsyncEnumerable",
    "OrderedEnumerable",
    "install",
    "uninstall",
]
