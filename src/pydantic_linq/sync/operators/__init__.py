"""Operator layer: one mixin per LINQ operator category (as grouped in the .NET docs)."""

from .aggregation import Aggregation
from .concatenation import Concatenation
from .conversion import Conversion
from .element import Element
from .equality import Equality
from .filtering import Filtering
from .generation import Generation
from .grouping import GroupingOps
from .joining import Joining
from .partitioning import Partitioning
from .projection import Projection
from .quantifiers import Quantifiers
from .sets import Sets
from .sorting import Sorting

__all__ = [
    "Aggregation",
    "Concatenation",
    "Conversion",
    "Element",
    "Equality",
    "Filtering",
    "Generation",
    "GroupingOps",
    "Joining",
    "Partitioning",
    "Projection",
    "Quantifiers",
    "Sets",
    "Sorting",
]
