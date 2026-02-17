import json
import uuid

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.logging.stdlib.logger import StdlibLogger
from mersal.messages.message_headers import MessageHeaders
from mersal.messages.transport_message import TransportMessage
from mersal.pipeline import RecursivePipelineInvoker
from mersal.pipeline.default_pipeline import (
    DefaultIncomingPipeline,
    DefaultOutgoingPipeline,
)
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.incoming_step_context import IncomingStepContext
from mersal.transport import (
    DefaultTransactionContextWithOwningApp,
    TransactionContext,
    Transport,
)
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPlugin,
    InMemoryTransportPluginConfig,
)
from mersal.transport.transport_decorator_plugin import TransportDecoratorPlugin
from mersal.types import AsyncAnyCallable
from mersal.workers.anyio import AnyioWorker, AnyioWorkerFactory
from mersal_testing.test_doubles import TransportMessageBuilder
from mersal_testing.transport.transport_decorator_helper import (
    TransportDecoratorHelper,
)

__all__ = (
    "HappyStep",
    "TestAnyioWorker",
    "ThrowingStep",
)


pytestmark = pytest.mark.anyio


class ThrowingStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable):
        transaction_context: TransactionContext = context.load(TransactionContext)
        transaction_context.set_result(False, False)
        raise Exception()


class HappyStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable):
        transaction_context: TransactionContext = context.load(TransactionContext)
        transaction_context.set_result(True, True)


class VariableSpeedStep(IncomingStep):
    def __init__(self, results: list[str]) -> None:
        self.results = results

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable):
        transaction_context: TransactionContext = context.load(TransactionContext)
        transaction_context.set_result(True, True)
        message = context.load(TransportMessage)
        delay = float(message.headers["delay"])
        label = str(message.headers["label"])
        await sleep(delay)
        self.results.append(label)


def _build_message_with_headers(**extra_headers: object) -> TransportMessage:
    data = {"a": 10}
    json_data = json.dumps(data)
    _bytes = bytes(json_data, "utf-8")
    headers = MessageHeaders(message_id=uuid.uuid4())
    for key, value in extra_headers.items():
        headers[key] = value
    return TransportMessage(body=_bytes, headers=headers)


class TestAnyioWorker:
    @pytest.fixture
    def incoming_pipeline(self) -> DefaultIncomingPipeline:
        return DefaultIncomingPipeline()

    @pytest.fixture
    def pipeline_invoker(self, incoming_pipeline: DefaultIncomingPipeline) -> RecursivePipelineInvoker:
        outgoing_pipeline = DefaultOutgoingPipeline()
        return RecursivePipelineInvoker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)

    async def test_logs_unhandled_exception_when_receiving(self, caplog, pipeline_invoker: RecursivePipelineInvoker):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        def throw():
            raise Exception()

        subject._receive_message = throw

        async with subject:
            await sleep(0)

        assert caplog.text

    async def test_logs_unhandled_exception_when_receiving_message_from_transport(
        self, caplog, pipeline_invoker: RecursivePipelineInvoker
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        async def transport_throw(_):
            raise Exception()

        transport.receive = transport_throw  # pyright: ignore[reportAttributeAccessIssue]

        async with subject:
            await sleep(0)

        assert caplog.text

    async def test_should_close_transaction_context_at_the_end(
        self, caplog, pipeline_invoker: RecursivePipelineInvoker
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        _transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        transport = TransportDecoratorHelper(_transport)

        called = False

        async def on_close(transaction_context: TransactionContext):
            nonlocal called
            called = True

        def hook(transaction_context: TransactionContext):
            transaction_context.on_close(on_close)

        transport.append_before_receive_hook(hook)
        factory = AnyioWorkerFactory(
            transport, pipeline_invoker=pipeline_invoker, logger=StdlibLogger(), max_parallelism=1
        )
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        async with subject:
            await sleep(0)

        assert called

    async def test_should_use_the_correct_transaction_context(self, caplog):
        network = InMemoryNetwork()
        transport_decorator: TransportDecoratorHelper | None = None

        def transport_decorator_factory(transport: Transport):
            nonlocal transport_decorator
            if transport_decorator:
                return transport_decorator
            transport_decorator = TransportDecoratorHelper(transport)
            return transport_decorator

        plugins = [
            InMemoryTransportPlugin(InMemoryTransportPluginConfig(network, "moon")),
            TransportDecoratorPlugin(transport_decorator_factory),
        ]
        app = Mersal("m1", BuiltinHandlerActivator(), plugins=plugins)

        subject: AnyioWorker = app.worker  # type: ignore

        async with subject:
            await sleep(0)

        assert transport_decorator
        assert isinstance(transport_decorator._receive[0], DefaultTransactionContextWithOwningApp)
        assert transport_decorator._receive[0].app == app

    async def test_logs_unhandled_exception_when_handling_message(
        self,
        caplog,
        pipeline_invoker: RecursivePipelineInvoker,
        incoming_pipeline: DefaultIncomingPipeline,
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        incoming_pipeline.append_step(ThrowingStep())
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        network.deliver(queue_address, TransportMessageBuilder.build())
        async with subject:
            await sleep(0)

        assert caplog.text

    async def test_logs_unhandled_exception_when_completing_transaction(
        self, caplog, pipeline_invoker: RecursivePipelineInvoker
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        network.deliver(queue_address, TransportMessageBuilder.build())
        async with subject:
            await sleep(0)

        assert caplog.text

    async def test_happy_path(
        self,
        caplog,
        pipeline_invoker: RecursivePipelineInvoker,
        incoming_pipeline: DefaultIncomingPipeline,
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        incoming_pipeline.append(HappyStep())
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        worker_name = "Worker-1"
        subject = factory.create_worker(worker_name)

        network.deliver(queue_address, TransportMessageBuilder.build())
        async with subject:
            await sleep(0)

        assert not network.get_next(queue_address)

    async def test_processes_messages_concurrently(
        self,
        pipeline_invoker: RecursivePipelineInvoker,
        incoming_pipeline: DefaultIncomingPipeline,
    ):
        results: list[str] = []
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        incoming_pipeline.append(VariableSpeedStep(results))
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=5)
        subject = factory.create_worker("Worker-1")

        network.deliver(queue_address, _build_message_with_headers(delay=0.3, label="slow"))
        network.deliver(queue_address, _build_message_with_headers(delay=0.05, label="fast"))

        async with subject:
            await sleep(0.5)

        assert results == ["fast", "slow"]

    async def test_backpressure_limits_concurrent_processing(
        self,
        pipeline_invoker: RecursivePipelineInvoker,
        incoming_pipeline: DefaultIncomingPipeline,
    ):
        results: list[str] = []
        network = InMemoryNetwork()
        queue_address = "test-queue"
        transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        incoming_pipeline.append(VariableSpeedStep(results))
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=1)
        subject = factory.create_worker("Worker-1")

        network.deliver(queue_address, _build_message_with_headers(delay=0.3, label="slow"))
        network.deliver(queue_address, _build_message_with_headers(delay=0.05, label="fast"))

        async with subject:
            await sleep(0.5)

        assert results == ["slow", "fast"]

    async def test_transaction_context_closed_for_each_concurrent_message(
        self,
        pipeline_invoker: RecursivePipelineInvoker,
        incoming_pipeline: DefaultIncomingPipeline,
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        _transport = InMemoryTransport(InMemoryTransportConfig(network, queue_address))
        transport = TransportDecoratorHelper(_transport)

        close_calls: list[TransactionContext] = []

        async def on_close(transaction_context: TransactionContext):
            close_calls.append(transaction_context)

        def hook(transaction_context: TransactionContext):
            transaction_context.on_close(on_close)

        transport.append_before_receive_hook(hook)
        incoming_pipeline.append(HappyStep())
        factory = AnyioWorkerFactory(transport, pipeline_invoker, logger=StdlibLogger(), max_parallelism=5)
        subject = factory.create_worker("Worker-1")

        network.deliver(queue_address, TransportMessageBuilder.build())
        network.deliver(queue_address, TransportMessageBuilder.build())

        async with subject:
            await sleep(0.1)

        # close() should have been called for each message's transaction context
        # plus the empty-receive iterations that also close their contexts
        assert len(close_calls) >= 2
