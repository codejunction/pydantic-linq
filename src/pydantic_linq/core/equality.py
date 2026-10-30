from collections.abc import Hashable, Iterable
from typing import Any


class EqSet:
    """Set using value equality that also accepts unhashable items (e.g. non-frozen pydantic models).

    ponytail: unhashable items fall back to an O(n) list scan; freeze the model (hashable) for O(1).
    """

    __slots__ = ("_hashed", "_unhashed")

    def __init__(self, items: Iterable[Any] = ()) -> None:
        self._hashed: set[Any] = set()
        self._unhashed: list[Any] = []
        for item in items:
            self.add(item)

    def add(self, item: Any) -> bool:
        """Add item; return True if it was not present."""
        if isinstance(item, Hashable):
            try:
                if item in self._hashed:
                    return False
                self._hashed.add(item)
                return True
            except TypeError:  # hashable type, unhashable value, e.g. tuple holding a list
                pass
        if item in self._unhashed:
            return False
        self._unhashed.append(item)
        return True

    def remove(self, item: Any) -> bool:
        """Remove item; return True if it was present."""
        try:
            self._hashed.remove(item)
            return True
        except (KeyError, TypeError):
            pass
        try:
            self._unhashed.remove(item)
            return True
        except ValueError:
            return False

    def __contains__(self, item: Any) -> bool:
        try:
            if item in self._hashed:
                return True
        except TypeError:
            pass
        return item in self._unhashed
