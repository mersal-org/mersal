from .callable_types import (
    AsyncAnyCallable,
    AsyncTransactionContextCallable,
    Factory,
    LifespanHook,
)


class Empty:
    """A sentinel class used as placeholder."""


EmptyType = type[Empty]

__all__ = [
    "AsyncAnyCallable",
    "AsyncTransactionContextCallable",
    "Empty",
    "EmptyType",
    "Factory",
    "LifespanHook",
]
