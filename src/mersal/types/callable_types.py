from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from mersal.types.helper_types import SyncOrAsyncUnion

if TYPE_CHECKING:
    from mersal.transport.transaction_context import TransactionContext

T = TypeVar("T")
AsyncAnyCallable: TypeAlias = Callable[..., Awaitable[Any]]
AsyncTransactionContextCallable: TypeAlias = Callable[["TransactionContext"], Awaitable[Any]]

LifespanHook = Callable[[], SyncOrAsyncUnion[Any]]
Factory = Callable[..., T]
