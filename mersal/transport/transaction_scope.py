from collections.abc import Callable
from typing import Any

from mersal.logging import Logger
from mersal.logging.null_logger import NullLogger

from .ambient_context import AmbientContext
from .default_transaction_context import DefaultTransactionContext
from .transaction_context import TransactionContext

__all__ = ("TransactionScope",)


class TransactionScope:
    __slots__ = [
        "__previous_transaction_context",
        "logger",
        "transaction_context",
    ]

    def __init__(
        self,
        transaction_context_factory: Callable[..., TransactionContext] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self.__previous_transaction_context = AmbientContext().current
        self.transaction_context: TransactionContext = (
            transaction_context_factory() if transaction_context_factory else DefaultTransactionContext()
        )
        self.logger: Logger = logger if logger is not None else NullLogger()

    async def __aenter__(self) -> "TransactionScope":
        AmbientContext().current = self.transaction_context
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def complete(self) -> None:
        self.transaction_context.set_result(commit=True, ack=True)
        await self.transaction_context.complete()

    async def close(self) -> None:
        try:
            await self.transaction_context.close()
        except:  # noqa: E722
            self.logger.exception("transaction_scope.close.error")
        finally:
            AmbientContext().current = self.__previous_transaction_context
