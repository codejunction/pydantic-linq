"""Equality: SequenceEqual."""

from __future__ import annotations

import itertools
from collections.abc import Iterable

from ...core import MISSING
from ..base import EnumerableBase


class Equality[T](EnumerableBase[T]):
    __slots__ = ()

    def sequence_equal(self, second: Iterable[T]) -> bool:
        return all(a == b for a, b in itertools.zip_longest(self, second, fillvalue=MISSING))
