"""Lets Enumerable[Model] be a pydantic field type: validated like list[Model], serialized as a list."""

from collections.abc import Callable, Iterable
from typing import Any

from pydantic_core import core_schema


def sequence_schema(cls: Callable[[Iterable[Any]], Any], source: Any, handler: Any) -> core_schema.CoreSchema:
    args = getattr(source, "__args__", None)
    item_type = args[0] if args else Any
    return core_schema.no_info_before_validator_function(
        # list[T] validation rejects arbitrary iterables, so unwrap our own sequences first
        lambda v: list(v) if isinstance(v, cls) else v,  # type: ignore[arg-type]
        core_schema.no_info_after_validator_function(cls, handler.generate_schema(list[item_type])),
        serialization=core_schema.plain_serializer_function_ser_schema(list),
    )
