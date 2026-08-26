from __future__ import annotations

import time
import types
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Literal, Self

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
from mersal.workers.backoff import DefaultWorkerBackoffStrategy, WorkerBackoffStrategy

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
        backoff_strategy: WorkerBackoffStrategy | None = None,
        stop_grace_period: float | None = None,
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
        self._backoff_strategy = backoff_strategy if backoff_strategy is not None else DefaultWorkerBackoffStrategy()
        self._stop_grace_period = stop_grace_period
        self._shielded_scopes: set[CancelScope] = set()
        self.last_heartbeat: float | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def heartbeat_age(self) -> float | None:
        """Seconds since the receive loop last made progress, or None before the first beat."""
        if self.last_heartbeat is None:
            return None
        return time.monotonic() - self.last_heartbeat

    async def _stop(self) -> None:
        self._running = False
        if self._cancel_scope:
            self._cancel_scope.cancel()
        if self._stop_grace_period is not None:
            # In-flight handlers run in shielded scopes that outlive the
            # cancellation above; a deadline on each scope bounds the drain so
            # a stuck handler cannot wedge graceful shutdown.
            deadline = anyio.current_time() + self._stop_grace_period
            for scope in self._shielded_scopes:
                scope.deadline = deadline
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def __aenter__(self) -> Self:
        self.logger.info(
            "worker.configured",
            worker=self.name,
            max_parallelism=self._max_parallelism,
            stop_grace_period=self._stop_grace_period,
            backoff_strategy=type(self._backoff_strategy).__name__,
        )
        self._exit_stack = AsyncExitStack()
        self._parallelism_limiter = anyio.Semaphore(self._max_parallelism)
        self._processing_tg = anyio.create_task_group()
        await self._exit_stack.enter_async_context(self._processing_tg)
        self._cancel_scope = self._processing_tg.cancel_scope
        self.last_heartbeat = time.monotonic()
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
            self.last_heartbeat = time.monotonic()
            try:
                outcome = await self._receive_message()
            except Exception:
                self.logger.exception("worker.receive.error", worker=self.name)
                outcome = "error"
            if outcome == "received":
                self._backoff_strategy.reset()
            elif outcome == "empty":
                await self._backoff_strategy.wait_no_message()
            else:
                await self._backoff_strategy.wait_error()
            await anyio.lowlevel.checkpoint()

    async def _receive_message(self) -> Literal["received", "empty", "error"]:
        if self._parallelism_limiter is None or self._processing_tg is None:
            raise RuntimeError("Worker must be entered as an async context manager before receiving messages")
        await self._parallelism_limiter.acquire()
        outcome: Literal["received", "empty", "error"] = "empty"
        handed_off = False
        transaction_context = DefaultTransactionContextWithOwningApp(self.app)
        try:
            await transaction_context.__aenter__()
            transport_message: TransportMessage | None = None
            try:
                transport_message = await self.transport.receive(transaction_context)
            except Exception:
                self.logger.exception("worker.transport.receive.error", worker=self.name)
                outcome = "error"

            if transport_message:
                _ = self._processing_tg.start_soon(
                    self._process_message_in_background, transport_message, transaction_context
                )
                handed_off = True
                outcome = "received"
            else:
                await transaction_context.__aexit__(None, None, None)
        finally:
            if not handed_off:
                self._parallelism_limiter.release()
        return outcome

    async def _process_message_in_background(
        self, message: TransportMessage, transaction_context: TransactionContext
    ) -> None:
        if self._parallelism_limiter is None:
            raise RuntimeError("Worker must be entered as an async context manager before processing messages")
        scope = CancelScope(shield=True)
        self._shielded_scopes.add(scope)
        try:
            with scope:
                try:
                    await self._process_message(message, transaction_context)
                finally:
                    # The stop-grace deadline may have cancelled this scope;
                    # shield the transaction close so ack/nack still runs.
                    with CancelScope(shield=True):
                        try:
                            await transaction_context.__aexit__(None, None, None)
                        except Exception:
                            self.logger.exception("worker.transaction.close.error", message=message.message_label)
                    self._parallelism_limiter.release()
        finally:
            self._shielded_scopes.discard(scope)

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
