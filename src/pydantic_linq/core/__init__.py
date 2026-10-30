"""Core layer: building blocks shared by the sync and async layers. Depends on nothing else in the package."""

from .equality import EqSet
from .errors import InvalidOperationError
from .grouping import group
from .sentinel import MISSING

__all__ = ["MISSING", "EqSet", "InvalidOperationError", "group"]
