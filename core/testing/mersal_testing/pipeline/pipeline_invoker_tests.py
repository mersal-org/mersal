import time
from collections.abc import Callable
from typing import Any

import anyio
import pytest

from mersal.pipeline import (
    IncomingStepContext,
    OutgoingStepContext,
)
from mersal.pipeline.default_pipeline import (
    DefaultIncomingPipeline,
    DefaultOutgoingPipeline,
)
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.outgoing_step import OutgoingStep
from mersal.pipeline.pipeline_invoker import PipelineInvoker
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.transport import DefaultTransactionContext
from mersal.types import AsyncAnyCallable
from mersal_testing.test_doubles import LogicalMessageBuilder, TransportMessageBuilder

__all__ = (
    "DummyIncomingStep",
    "DummyOutgoingStep",
    "PipelineInvokerTestsBase",
    "SleepingIncomingStep",
)


pytestmark = pytest.mark.anyio


class SleepingIncomingStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        await anyio.sleep(0)
        await next_step()


class DummyIncomingStep(IncomingStep):
    def __init__(self, order: int) -> None:
        self.order = order

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        data: list[int] = context.load_keys("dummy-data")
        data.append(self.order)
        await next_step()


class DummyOutgoingStep(OutgoingStep):
    def __init__(self, order: int) -> None:
        self.order = order

    async def __call__(self, context: OutgoingStepContext, next_step: AsyncAnyCallable) -> None:
        data: list[int] = context.load_keys("dummy-data")
        data.append(self.order)
        await next_step()


class PipelineInvokerTestsBase:
    @pytest.fixture
    def pipeline_invoker_maker(self) -> Callable[..., PipelineInvoker]:
        def maker(**kwargs: Any) -> PipelineInvoker:
            raise NotImplementedError()

        return maker

    async def test_invokes_incoming(self, pipeline_invoker_maker: Callable[..., PipelineInvoker]) -> None:
        incoming_pipeline = DefaultIncomingPipeline()
        outgoing_pipeline = DefaultOutgoingPipeline()
        for i in range(5):
            incoming_pipeline.append_step(DummyIncomingStep(i))
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()

        context = IncomingStepContext(message=transport_message, transaction_context=transaction_context)
        data: list[int] = []
        context.save_keys("dummy-data", data)
        subject = pipeline_invoker_maker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)
        await subject(context)
        assert data == list(range(5))

    async def test_invokes_outgoing(self, pipeline_invoker_maker: Callable[..., PipelineInvoker]) -> None:
        incoming_pipeline = DefaultIncomingPipeline()
        outgoing_pipeline = DefaultOutgoingPipeline()
        for i in range(5):
            outgoing_pipeline.append_step(DummyOutgoingStep(i))
        logical_message = LogicalMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"sun"})

        context = OutgoingStepContext(
            message=logical_message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        data: list[int] = []
        context.save_keys("dummy-data", data)
        subject = pipeline_invoker_maker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)
        await subject(context)
        assert data == list(range(5))

    """
    There is no difference between the recursive and iterative invoker.

    Benchmarks for the time being:
    100_000 iterations took 32 secs -> ~3125 message/sec using asyncio
    100_000 iterations took 47 secs -> ~2125 message/sec using trio

    This is crazy compared to the performance of Reapp in this regard.

    The actual performance will be worse with encoding/decoding + other
    processing.
    """

    @pytest.mark.slow
    async def test_invoke_performance(self, pipeline_invoker_maker: Callable[..., PipelineInvoker]) -> None:
        incoming_pipeline = DefaultIncomingPipeline()
        outgoing_pipeline = DefaultOutgoingPipeline()

        for _ in range(10):
            incoming_pipeline.append_step(SleepingIncomingStep())

        subject = pipeline_invoker_maker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)
        t0 = time.time()
        for _ in range(100000):
            transport_message = TransportMessageBuilder.build()
            transaction_context = DefaultTransactionContext()

            context = IncomingStepContext(message=transport_message, transaction_context=transaction_context)
            await subject(context)
        t1 = time.time()

        elapsed_time = t1 - t0
        print("Elapsed time", elapsed_time)  # noqa: T201
        assert 0
