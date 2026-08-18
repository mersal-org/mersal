from __future__ import annotations

import types
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Self

import anyio
import anyio.abc
import anyio.lowlevel
from anyio import CancelScope

from mersal.pipeline import IncomingStepContext, PipelineInvoker
from mersal.transport import (
    DefaultTransactionContextWithOwningApp,
    TransactionContext,
    Transport,
)
from mersal.transport.ambient_context import AmbientContext

if TYPE_CHECKING:
    from mersal.core.app import Mersal
    from mersal.logging import Logger
    from mersal.messages import TransportMessage

__all__ = ("AnyioWorker",)


class AnyioWorker:
    def __init__(
        self,
        name: str,
        transport: Transport,
        app: Mersal,
        pipeline_invoker: PipelineInvoker,
        max_parallelism: int,
        logger: Logger,
    ) -> None:
        self.logger = logger
        self.name = name
        self.transport = transport
        self.app = app
        self.pipeline_invoker = pipeline_invoker
        self._exit_stack: AsyncExitStack | None = None
        self._cancel_scope: CancelScope | None = None
        self._running = False
        self._max_parallelism = max_parallelism
        self._parallelism_limiter: anyio.Semaphore | None = None
        self._processing_tg: anyio.abc.TaskGroup | None = None

    async def _stop(self) -> None:
        self._running = False
        if self._cancel_scope:
            self._cancel_scope.cancel()
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def __aenter__(self) -> Self:
        self._exit_stack = AsyncExitStack()
        self._parallelism_limiter = anyio.Semaphore(self._max_parallelism)
        self._processing_tg = anyio.create_task_group()
        await self._exit_stack.enter_async_context(self._processing_tg)
        self._cancel_scope = self._processing_tg.cancel_scope
        _ = self._processing_tg.start_soon(self._run)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self._stop()
        self._exit_stack = None

    async def _run(self) -> None:
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
                self.logger.exception("worker.receive.error", worker=self.name)
            await anyio.lowlevel.checkpoint()

    async def _receive_message(self) -> None:
        if self._parallelism_limiter is None or self._processing_tg is None:
            raise RuntimeError("Worker must be entered as an async context manager before receiving messages")
        await self._parallelism_limiter.acquire()
        handed_off = False
        transaction_context = DefaultTransactionContextWithOwningApp(self.app)
        try:
            await transaction_context.__aenter__()
            transport_message: TransportMessage | None = None
            try:
                transport_message = await self.transport.receive(transaction_context)
            except Exception:
                self.logger.exception("worker.transport.receive.error", worker=self.name)

            if transport_message:
                _ = self._processing_tg.start_soon(
                    self._process_message_in_background, transport_message, transaction_context
                )
                handed_off = True
            else:
                await transaction_context.__aexit__(None, None, None)
        finally:
            if not handed_off:
                self._parallelism_limiter.release()

    async def _process_message_in_background(
        self, message: TransportMessage, transaction_context: TransactionContext
    ) -> None:
        if self._parallelism_limiter is None:
            raise RuntimeError("Worker must be entered as an async context manager before processing messages")
        with CancelScope(shield=True):
            try:
                await self._process_message(message, transaction_context)
            finally:
                try:
                    await transaction_context.__aexit__(None, None, None)
                except Exception:
                    self.logger.exception("worker.transaction.close.error", message=message.message_label)
                self._parallelism_limiter.release()

    async def _process_message(self, message: TransportMessage, transaction_context: TransactionContext) -> None:
        try:
            AmbientContext().current = transaction_context
            step_context = IncomingStepContext(message, transaction_context)
            await self.pipeline_invoker(step_context)
            try:
                await transaction_context.complete()
            except Exception:
                self.logger.exception("worker.transaction.complete.error", message=message.message_label)
        except Exception:
            self.logger.exception("worker.message.error", message=message.message_label)
        finally:
            AmbientContext().current = None
