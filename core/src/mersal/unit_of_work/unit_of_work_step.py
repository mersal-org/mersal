from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mersal.pipeline import IncomingStepContext, MessageContext
from mersal.pipeline.incoming_step import IncomingStep
from mersal.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from mersal.types.callable_types import AsyncAnyCallable, AsyncTransactionContextCallable
    from mersal.unit_of_work.config import (
        UnitOfWorkConfig,
    )

__all__ = ("UnitOfWorkStep",)


class UnitOfWorkStep(IncomingStep):
    def __init__(self, config: UnitOfWorkConfig) -> None:
        self._uow_factory = config.uow_factory
        self._commit_action = config.commit_action
        self._rollback_action = config.rollback_action
        self._close_action = config.close_action
        self.commit_with_transaction = config.commit_with_transaction

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        message_context = MessageContext.current()
        if not message_context:
            raise Exception("Not inside a transaction")

        uow = await AsyncCallable(self._uow_factory)(message_context)
        message_context.transaction_context.items["uow"] = uow
        try:
            await next_step()
            await self._commit(message_context, uow)
        except Exception:
            await self._rollback(message_context, uow)
            raise

    async def _commit(self, message_context: MessageContext, uow: Any) -> None:
        transaction_context = message_context.transaction_context

        def commit_action() -> Awaitable[Any]:
            return self._commit_action(message_context, uow)

        def close_action() -> Awaitable[Any]:
            return self._close_action(message_context, uow)

        if not self.commit_with_transaction:
            await commit_action()
            await close_action()
        else:

            async def _action(_: AsyncTransactionContextCallable) -> None:
                await commit_action()

            async def _close_action(_: AsyncTransactionContextCallable) -> None:
                await close_action()

            transaction_context.on_commit(_action)
            transaction_context.on_close(_close_action)

    async def _rollback(self, message_context: MessageContext, uow: Any) -> None:
        transaction_context = message_context.transaction_context

        def rollback_action() -> Awaitable[Any]:
            return self._rollback_action(message_context, uow)

        def close_action() -> Awaitable[Any]:
            return self._close_action(message_context, uow)

        if not self.commit_with_transaction:
            await rollback_action()
            await close_action()
        else:

            async def _action(_: AsyncTransactionContextCallable) -> None:
                await rollback_action()

            async def _close_action(_: AsyncTransactionContextCallable) -> None:
                await close_action()

            transaction_context.on_rollback(_action)
            transaction_context.on_close(_close_action)
