from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, Protocol, Self

if TYPE_CHECKING:
    from collections.abc import Callable

    from mersal.types import AsyncTransactionContextCallable

__all__ = ("TransactionContext",)


class TransactionContext(Protocol):
    items: dict[str | type, Any]

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...

    def on_commit(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_rollback(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_ack(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_nack(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_close(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_error(self, action: Callable[[Exception], None]) -> None: ...

    def set_result(self, commit: bool, ack: bool) -> None: ...

    async def complete(self) -> None: ...

    async def close(self) -> None: ...
