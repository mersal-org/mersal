from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias, TypeVar

from mersal.types.helper_types import SyncOrAsyncUnion

T = TypeVar("T")
AsyncAnyCallable: TypeAlias = Callable[..., Awaitable[Any]]
AsyncTransactionContextCallable: TypeAlias = Callable[
    ["TransactionContext"], Awaitable[Any]  # type: ignore[name-defined] # noqa: F821
]

LifespanHook = Callable[[], SyncOrAsyncUnion[Any]]
Factory = Callable[..., T]
