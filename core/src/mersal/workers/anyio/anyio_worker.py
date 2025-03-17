from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

import anyio
from anyio import CancelScope, sleep

from mersal.pipeline import IncomingStepContext, PipelineInvoker
from mersal.transport import (
    DefaultTransactionContextWithOwningApp,
    TransactionContext,
    Transport,
)
from mersal.transport.ambient_context import AmbientContext

if TYPE_CHECKING:
    from mersal.app import Mersal
    from mersal.messages import TransportMessage

__all__ = ("AnyioWorker",)


class AnyioWorker:
    def __init__(
        self,
        name: str,
        transport: Transport,
        app: Mersal,
        pipeline_invoker: PipelineInvoker,
    ) -> None:
        self.logger = logging.getLogger("mersal.defaultWorker")
        self.name = name
        self.transport = transport
        self.app = app
        self.pipeline_invoker = pipeline_invoker
        self._exit_stack: AsyncExitStack | None = None
        self._cancel_scope: CancelScope | None = None
        self._running = False

    async def _stop(self) -> None:
        self.logger.info("The worker %r will stop now.", self.name)
        self._running = False
        if self._cancel_scope:
            self._cancel_scope.cancel()
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def __aenter__(self) -> AnyioWorker:
        self.logger.info("The worker %r will start now.", self.name)
        self._exit_stack = AsyncExitStack()
        task_group = anyio.create_task_group()
        await self._exit_stack.enter_async_context(task_group)
        self._cancel_scope = task_group.cancel_scope
        task_group.start_soon(self.start)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        await self._stop()
        self._exit_stack = None

    async def start(self) -> None:
        try:
            self._running = True
            await self._start()
        except anyio.get_cancelled_exc_class():
            self._running = False
            raise

    async def _start(self) -> None:
        while True:
            try:
                await self._receive_message()
            except Exception:
                self.logger.exception(
                    "Unhandled exception in worker: %s while trying to receive the message.",
                    self.name,
                )
            await sleep(0)

    async def _receive_message(self) -> None:
        async with DefaultTransactionContextWithOwningApp(self.app) as transaction_context:
            transport_message: TransportMessage | None = None
            try:
                transport_message = await self.transport.receive(transaction_context)
            except Exception:
                self.logger.exception(
                    "Unhandled exception in worker: %s while trying to receive next message from transport",
                    self.name,
                )

            if transport_message:
                with CancelScope(shield=True):
                    await self._process_message(transport_message, transaction_context)

    async def _process_message(self, message: TransportMessage, transaction_context: TransactionContext) -> None:
        try:
            AmbientContext().current = transaction_context
            step_context = IncomingStepContext(message, transaction_context)
            await self.pipeline_invoker(step_context)
            try:
                await transaction_context.complete()
            except Exception:
                self.logger.exception(
                    "Exception while trying to complete the transaction context for message %r",
                    message.message_label,
                )
        except Exception:
            self.logger.exception("Unhandled exception while handling message %r", message.message_label)
        finally:
            AmbientContext().current = None
