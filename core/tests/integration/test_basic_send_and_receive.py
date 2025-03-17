import uuid

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.routing.default import (
    DefaultRouterRegistrationConfig,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.message_handlers.message_handler_that_counts import (
    MessageHandlerThatCounts,
)
from mersal_testing.message_handlers.message_handler_that_stores_the_message import (
    MessageHandlerThatStoresTheMessage,
)
from mersal_testing.messages import BasicMessageA

__all__ = (
    "DummyMessage",
    "DummyMessage2",
    "DummyMessageHandler",
    "TestBasicSendAndReceiveIntegration",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    def __init__(self):
        self.internal = []


class DummyMessage2:
    def __init__(self):
        self.internal = []


class DummyMessageHandler:
    def __init__(self, delay: int | None = None) -> None:
        self.delay = delay

    async def __call__(self, message: DummyMessage | DummyMessage2):
        if self.delay is not None:
            await sleep(self.delay)
        message.internal.append(1)


class TestBasicSendAndReceiveIntegration:
    async def test_sending_and_receiving(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = BasicMessageA()
        handler1: MessageHandlerThatStoresTheMessage | None = None
        handler2: MessageHandlerThatCounts | None = None

        def handler1_factory(message_context):
            nonlocal handler1
            handler1 = MessageHandlerThatStoresTheMessage(message_context)
            return handler1

        handler2 = MessageHandlerThatCounts()

        activator.register(BasicMessageA, lambda m, b: handler1_factory(m))
        activator.register(BasicMessageA, lambda _, __: handler2)

        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        await app.send_local(message)
        await app.start()
        await sleep(1)
        await app.stop()
        assert handler1
        assert handler1.headers.get("message_id")
        assert handler2.count == 1

    async def test_sending_and_receiving_with_multiple_handlers(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler())
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler())
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        await app.send_local(message, {})
        async with app:
            await sleep(0)

        assert not app.worker._running  # pyright: ignore[reportAttributeAccessIssue]
        assert message.internal == [1, 1]

    async def test_cancelling_while_processing_a_message(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler(1))
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        await app.send_local(message, {})
        async with app:
            await sleep(0)

        assert message.internal == [1]

    async def test_sending_and_receiving_using_default_router_plugin(self):
        network = InMemoryNetwork()
        queue_address1 = "test-queue"
        queue_address2 = "test-queue2"
        activator = BuiltinHandlerActivator()
        _ = DummyMessage()
        message2 = DummyMessage2()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler())
        activator.register(DummyMessage2, lambda m, b: DummyMessageHandler())
        router_plugin = DefaultRouterRegistrationConfig(
            {queue_address1: [DummyMessage], queue_address2: [DummyMessage2]}
        ).plugin
        plugins1 = [
            InMemoryTransportPluginConfig(network, queue_address1).plugin,
            router_plugin,
        ]
        plugins2 = [
            InMemoryTransportPluginConfig(network, queue_address2).plugin,
            router_plugin,
        ]
        app1 = Mersal("m1", activator, plugins=plugins1)
        app2 = Mersal("m2", activator, plugins=plugins2)
        await app1.send(message2, {})
        async with app2:
            await sleep(0)

        assert message2.internal == [1]

    async def test_using_custom_messsage_id_generator(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = BasicMessageA()
        handler: MessageHandlerThatStoresTheMessage | None = None

        def handler1_factory(message_context):
            nonlocal handler
            handler = MessageHandlerThatStoresTheMessage(message_context)
            return handler

        activator.register(BasicMessageA, lambda m, b: handler1_factory(m))

        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        message_id = str(uuid.uuid4())
        app = Mersal("m1", activator, message_id_generator=lambda message: message_id, plugins=plugins)
        await app.send_local(message)
        await app.start()
        await sleep(1)
        await app.stop()
        assert handler
        assert handler.headers.get("message_id") == message_id
