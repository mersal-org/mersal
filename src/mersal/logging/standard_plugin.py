from __future__ import annotations

import time
import types
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Self

from mersal.logging.logger import Logger
from mersal.messages import LogicalMessage, TransportMessage
from mersal.pipeline import (
    IncomingPipeline,
    IncomingStepContext,
    OutgoingPipeline,
    OutgoingStepContext,
    PipelineInvoker,
)
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.pipeline.step_context import RETRY_ATTEMPTS_KEY, STEP_EXECUTION_COUNT_KEY
from mersal.plugins import Plugin
from mersal.retry import ErrorHandler
from mersal.workers import WorkerFactory

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from mersal.configuration import StandardConfigurator
    from mersal.core.app import Mersal
    from mersal.logging.config import LoggingConfig
    from mersal.pipeline.incoming_step import IncomingStep
    from mersal.pipeline.outgoing_step import OutgoingStep
    from mersal.transport import TransactionContext
    from mersal.types import AsyncAnyCallable
    from mersal.workers import Worker

__all__ = ("StandardLoggingPlugin",)


PipelineContext = Any  # Callable[..., AbstractContextManager]


@contextmanager
def _noop_context(**kwargs: Any) -> Iterator[None]:
    yield


def _step_name(step: Any) -> str:
    return type(step).__name__


def _extract_incoming_context(context: IncomingStepContext) -> dict[str, Any]:
    transport_message = context.load(TransportMessage)
    if not transport_message:  # type: ignore[truthy-bool]
        return {"message": "unknown", "pipeline": "incoming"}
    return {
        "pipeline": "incoming",
        "message": transport_message.message_label,
        "message_id": str(transport_message.headers.message_id),
        "message_type": transport_message.headers.message_type or transport_message.message_label,
    }


def _extract_outgoing_context(context: OutgoingStepContext) -> dict[str, Any]:
    logical_message = context.load(LogicalMessage)
    destinations = context.load(DestinationAddresses)
    result: dict[str, Any] = {"pipeline": "outgoing"}
    if logical_message:  # type: ignore[truthy-bool]
        result["message"] = logical_message.message_label
        result["message_id"] = str(logical_message.headers.message_id)
        result["message_type"] = logical_message.headers.message_type or logical_message.message_label
    else:
        result["message"] = "unknown"
    result["destinations"] = ",".join(destinations) if destinations else "unknown"  # type: ignore[truthy-bool]
    return result


# --- Step decorators ---


class _LoggingIncomingStep:
    def __init__(self, step: IncomingStep, logger: Logger) -> None:
        self._step = step
        self._logger = logger

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        step_name = _step_name(self._step)
        transport_message = context.load(TransportMessage)
        message_label = transport_message.message_label if transport_message else "unknown"  # type: ignore[truthy-bool]

        context.save_keys(STEP_EXECUTION_COUNT_KEY, (context.load_keys(STEP_EXECUTION_COUNT_KEY) or 0) + 1)

        logger = self._logger.bind(step=step_name, message=message_label, pipeline="incoming")

        logger.debug("step.execute")
        start = time.perf_counter()

        async def logged_next_step() -> None:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug("step.next", elapsed_ms=elapsed_ms)
            await next_step()

        try:
            await self._step(context, logged_next_step)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("step.error", elapsed_ms=elapsed_ms)
            raise


class _LoggingOutgoingStep:
    def __init__(self, step: OutgoingStep, logger: Logger) -> None:
        self._step = step
        self._logger = logger

    async def __call__(self, context: OutgoingStepContext, next_step: AsyncAnyCallable) -> None:
        step_name = _step_name(self._step)
        logical_message = context.load(LogicalMessage)
        message_label = logical_message.message_label if logical_message else "unknown"  # type: ignore[truthy-bool]

        destinations = context.load(DestinationAddresses)
        dest_str = ",".join(destinations) if destinations else "unknown"  # type: ignore[truthy-bool]

        context.save_keys(STEP_EXECUTION_COUNT_KEY, (context.load_keys(STEP_EXECUTION_COUNT_KEY) or 0) + 1)

        logger = self._logger.bind(step=step_name, message=message_label, destinations=dest_str, pipeline="outgoing")

        logger.debug("step.execute")
        start = time.perf_counter()

        async def logged_next_step() -> None:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug("step.next", elapsed_ms=elapsed_ms)
            await next_step()

        try:
            await self._step(context, logged_next_step)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("step.error", elapsed_ms=elapsed_ms)
            raise


# --- Pipeline decorators ---


class _LoggingIncomingPipeline:
    def __init__(self, pipeline: IncomingPipeline, logger: Logger) -> None:
        self._pipeline = pipeline
        self._logger = logger

    def __call__(self) -> Sequence[IncomingStep]:
        steps = self._pipeline()
        self._logger.info(
            "pipeline.initialized",
            pipeline="incoming",
            steps=[_step_name(s) for s in steps],
            step_count=len(steps),
        )
        return [_LoggingIncomingStep(step, self._logger) for step in steps]


class _LoggingOutgoingPipeline:
    def __init__(self, pipeline: OutgoingPipeline, logger: Logger) -> None:
        self._pipeline = pipeline
        self._logger = logger

    def __call__(self) -> Sequence[OutgoingStep]:
        steps = self._pipeline()
        self._logger.info(
            "pipeline.initialized",
            pipeline="outgoing",
            steps=[_step_name(s) for s in steps],
            step_count=len(steps),
        )
        return [_LoggingOutgoingStep(step, self._logger) for step in steps]


# --- Pipeline invoker decorator ---


class _LoggingPipelineInvoker:
    def __init__(self, invoker: PipelineInvoker, logger: Logger, pipeline_context: PipelineContext) -> None:
        self._invoker = invoker
        self._logger = logger
        self._pipeline_context = pipeline_context

    async def __call__(self, context: IncomingStepContext | OutgoingStepContext) -> None:
        if isinstance(context, IncomingStepContext):
            ctx = _extract_incoming_context(context)
        else:
            ctx = _extract_outgoing_context(context)

        logger = self._logger.bind(**ctx)

        with self._pipeline_context(**ctx):
            logger.debug("pipeline.invoke.start")
            start = time.perf_counter()

            outcome = "success"
            try:
                await self._invoker(context)
            except Exception:
                outcome = "error"
                raise
            finally:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                step_count = context.load_keys(STEP_EXECUTION_COUNT_KEY) or 0
                retry_attempts = context.load_keys(RETRY_ATTEMPTS_KEY)

                log = logger.error if outcome == "error" else logger.info
                log(
                    "pipeline.invoke",
                    canonical=True,
                    log_type="canonical-log-line",
                    outcome=outcome,
                    elapsed_ms=elapsed_ms,
                    step_count=step_count,
                    **({"retry_attempts": retry_attempts} if retry_attempts is not None else {}),
                )


# --- Error handler decorator ---


class _LoggingErrorHandler:
    def __init__(self, handler: ErrorHandler, logger: Logger) -> None:
        self._handler = handler
        self._logger = logger

    async def handle_poison_message(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
        exception: Exception,
    ) -> None:
        logger = self._logger.bind(
            message=message.message_label,
            message_id=str(message.headers.message_id),
            error_queue=getattr(self._handler, "error_queue_name", "unknown"),
        )
        logger.warning("deadletter.forward", exception=str(exception))
        try:
            await self._handler.handle_poison_message(message, transaction_context, exception)
            logger.info("deadletter.forwarded")
        except Exception:
            logger.error("deadletter.forward.error")
            raise


# --- Worker factory decorator ---


class _LoggingWorker:
    def __init__(self, worker: Worker, logger: Logger) -> None:
        self._worker = worker
        self._logger = logger.bind(worker=worker.name)

    @property
    def name(self) -> str:
        return self._worker.name

    @property
    def running(self) -> bool:
        return self._worker.running

    async def __call__(self) -> None:
        await self._worker()

    async def stop(self) -> None:
        self._logger.info("worker.stop")
        await self._worker.stop()

    async def __aenter__(self) -> Self:
        self._logger.info("worker.start")
        await self._worker.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self._worker.__aexit__(exc_type, exc_val, exc_tb)
        self._logger.info("worker.stopped")


class _LoggingWorkerFactory:
    def __init__(self, factory: WorkerFactory, logger: Logger) -> None:
        self._factory = factory
        self._logger = logger

    @property
    def app(self) -> Mersal:
        return self._factory.app

    @app.setter
    def app(self, value: Mersal) -> None:
        self._factory.app = value

    def create_worker(self, name: str) -> _LoggingWorker:
        worker = self._factory.create_worker(name)
        return _LoggingWorker(worker, self._logger)


# --- Plugin ---


class StandardLoggingPlugin(Plugin):
    def __init__(self, config: LoggingConfig, pipeline_context: PipelineContext | None = None) -> None:
        self._config = config
        self._pipeline_context = pipeline_context or _noop_context

    def __call__(self, configurator: StandardConfigurator) -> None:
        logger: Logger = self._config.configure()()
        configurator.register(Logger, lambda _: logger)

        pipeline_context = self._pipeline_context

        def decorate_incoming_pipeline(configurator: StandardConfigurator) -> _LoggingIncomingPipeline:
            pipeline = configurator.get(IncomingPipeline)  # type: ignore[type-abstract]
            return _LoggingIncomingPipeline(pipeline, configurator.get(Logger))  # type: ignore[type-abstract]

        def decorate_outgoing_pipeline(configurator: StandardConfigurator) -> _LoggingOutgoingPipeline:
            pipeline = configurator.get(OutgoingPipeline)  # type: ignore[type-abstract]
            return _LoggingOutgoingPipeline(pipeline, configurator.get(Logger))  # type: ignore[type-abstract]

        def decorate_pipeline_invoker(configurator: StandardConfigurator) -> _LoggingPipelineInvoker:
            invoker = configurator.get(PipelineInvoker)  # type: ignore[type-abstract]
            return _LoggingPipelineInvoker(invoker, configurator.get(Logger), pipeline_context)  # type: ignore[type-abstract]

        def decorate_error_handler(configurator: StandardConfigurator) -> _LoggingErrorHandler:
            handler = configurator.get(ErrorHandler)  # type: ignore[type-abstract]
            return _LoggingErrorHandler(handler, configurator.get(Logger))  # type: ignore[type-abstract]

        def decorate_worker_factory(configurator: StandardConfigurator) -> _LoggingWorkerFactory:
            factory = configurator.get(WorkerFactory)  # type: ignore[type-abstract]
            return _LoggingWorkerFactory(factory, configurator.get(Logger))  # type: ignore[type-abstract]

        configurator.decorate(IncomingPipeline, decorate_incoming_pipeline)
        configurator.decorate(OutgoingPipeline, decorate_outgoing_pipeline)
        configurator.decorate(PipelineInvoker, decorate_pipeline_invoker)
        configurator.decorate(ErrorHandler, decorate_error_handler)
        configurator.decorate(WorkerFactory, decorate_worker_factory)
