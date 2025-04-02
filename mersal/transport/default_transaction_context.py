from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .transaction_context import TransactionContext

if TYPE_CHECKING:
    from collections.abc import Callable

    from mersal.types import AsyncTransactionContextCallable

__all__ = (
    "DefaultTransactionContext",
    "InvalidTransactioContextStateError",
)


class DefaultTransactionContext(TransactionContext):
    def __init__(self) -> None:
        self.logger = logging.getLogger("mersal.defaultTransactionContext")
        self.items: dict[str | type, Any] = {}
        self._on_committed_actions: list[AsyncTransactionContextCallable] = []
        self._on_rollback_actions: list[AsyncTransactionContextCallable] = []
        self._on_ack_actions: list[AsyncTransactionContextCallable] = []
        self._on_nack_actions: list[AsyncTransactionContextCallable] = []
        self._on_closed_actions: list[AsyncTransactionContextCallable] = []
        self._on_error_actions: list[Callable[[Exception], None]] = []
        self._must_commit: bool | None = None
        self._must_ack: bool | None = None
        self._completed: bool = False
        self._closed: bool = False

    async def __aenter__(self) -> DefaultTransactionContext:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def on_commit(self, action: AsyncTransactionContextCallable) -> None:
        self._raise_exception_if_completed()
        self._on_committed_actions.append(action)

    def on_rollback(self, action: AsyncTransactionContextCallable) -> None:
        self._raise_exception_if_completed()
        self._on_rollback_actions.append(action)

    def on_ack(self, action: AsyncTransactionContextCallable) -> None:
        self._raise_exception_if_completed()
        self._on_ack_actions.append(action)

    def on_nack(self, action: AsyncTransactionContextCallable) -> None:
        self._raise_exception_if_completed()
        self._on_nack_actions.append(action)

    def on_close(self, action: AsyncTransactionContextCallable) -> None:
        self._raise_exception_if_completed()
        self._on_closed_actions.append(action)

    def on_error(self, action: Callable[[Exception], None]) -> None:
        self._on_error_actions.append(action)

    async def complete(self) -> None:
        if self._must_commit is None or self._must_ack is None:
            raise InvalidTransactioContextStateError(
                "Transaction state `complete` method called before calling `set_result`"
            )
        try:
            await self._try_to_commit_or_rollback()
            await self._ack_or_nack()
        except:
            raise
        finally:
            self._completed = True

    def set_result(self, commit: bool, ack: bool) -> None:
        self._must_commit = commit
        self._must_ack = ack

    async def close(self) -> None:
        if self._closed:
            return

        if not self._must_commit:
            await self._try_to_rollback_or_invoke_error()
        if not self._must_ack:
            await self._try_to_nack_or_invoke_error()
        try:
            await self._invoke_closed_actions()
        except Exception as e:  # noqa: BLE001
            self._invoke_on_error_actions(e)

        self._closed = True

    async def _commit_or_rollback(self) -> None:
        if self._must_commit:
            await self._invoke_committed_actions()
        else:
            await self._invoke_rollback_actions()

    async def _ack_or_nack(self) -> None:
        if self._must_ack:
            await self._invoke_ack_actions()
        else:
            await self._invoke_nack_actions()

    async def _try_to_commit_or_rollback(self) -> None:
        try:
            await self._commit_or_rollback()
        except:
            await self._try_to_nack_or_invoke_error()
            raise

    async def _try_to_nack_or_invoke_error(self) -> None:
        try:
            await self._invoke_nack_actions()
        except Exception as e:  # noqa: BLE001
            self._invoke_on_error_actions(e)

    async def _try_to_rollback_or_invoke_error(self) -> None:
        try:
            await self._invoke_rollback_actions()
        except Exception as e:  # noqa: BLE001
            self._invoke_on_error_actions(e)

    def _raise_exception_if_completed(self) -> None:
        if self._completed:
            raise InvalidTransactioContextStateError("TransactionContext has been completed, cannot add actions")

    async def _invoke_committed_actions(self) -> None:
        await self._invoke_actions(self._on_committed_actions)

    async def _invoke_rollback_actions(self) -> None:
        await self._invoke_actions(self._on_rollback_actions)

    async def _invoke_ack_actions(self) -> None:
        await self._invoke_actions(self._on_ack_actions)

    async def _invoke_nack_actions(self) -> None:
        await self._invoke_actions(self._on_nack_actions)

    async def _invoke_closed_actions(self) -> None:
        await self._invoke_actions(self._on_closed_actions)

    async def _invoke_actions(self, actions: list[AsyncTransactionContextCallable]) -> None:
        _actions = actions.copy()
        actions.clear()
        for action in _actions:
            await action(self)

    def _invoke_on_error_actions(self, exception: Exception) -> None:
        for action in self._on_error_actions:
            action(exception)


class InvalidTransactioContextStateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
