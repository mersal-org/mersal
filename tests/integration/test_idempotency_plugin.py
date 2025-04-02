import anyio
import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.idempotency import IdempotencyConfig
from mersal.persistence.in_memory.in_memory_message_tracker import (
    InMemoryMessageTracker,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = (
    "DummyMessage",
    "DummyMessageHandler",
    "TestIdempotencyPlugin",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    def __init__(self):
        self.internal = []


class DummyMessageHandler:
    def __init__(self, delay: int | None = None) -> None:
        self.delay = delay
        self.call_count = 0

    async def __call__(self, message: DummyMessage):
        if self.delay is not None:
            await sleep(self.delay)

        self.call_count += 1
        message.internal.append(1)


class TestIdempotencyPlugin:
    async def test_stops_invocation(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        handler = DummyMessageHandler()
        activator.register(DummyMessage, lambda m, b: handler)

        tracker = InMemoryMessageTracker()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            IdempotencyConfig(tracker=tracker, should_stop_invocation=True).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.send_local(message)
        await app.send_local(message)
        await app.start()
        await anyio.sleep(0)
        assert handler.call_count == 1

    async def test_continues_invocation(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        handler = DummyMessageHandler()
        activator.register(DummyMessage, lambda m, b: handler)

        tracker = InMemoryMessageTracker()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            IdempotencyConfig(tracker=tracker, should_stop_invocation=False).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.send_local(message)
        await app.send_local(message)
        await app.start()
        await anyio.sleep(0.1)
        assert handler.call_count == 2
