import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.lifespan.lifespan_hooks_registration_plugin import (
    LifespanHooksRegistrationPluginConfig,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = (
    "DummyMessage",
    "DummyMessageHandler",
    "TestLifespanPlugin",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    def __init__(self):
        self.internal = []


class DummyMessageHandler:
    def __init__(self, delay: int | None = None) -> None:
        self.delay = delay

    async def __call__(self, message: DummyMessage):
        if self.delay is not None:
            await sleep(self.delay)
        message.internal.append(1)


class TestLifespanPlugin:
    async def test_calling_on_startup_and_shutdown_hooks(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler())
        on_startup_call_count = 0
        on_shutdown_call_count = 0

        async def async_on_startup_hook():
            nonlocal on_startup_call_count
            on_startup_call_count += 1

        async def sync_on_startup_hook():
            nonlocal on_startup_call_count
            on_startup_call_count += 1

        async def async_on_shutdown_hook():
            nonlocal on_shutdown_call_count
            on_shutdown_call_count += 1

        async def sync_on_shutdown_hook():
            nonlocal on_shutdown_call_count
            on_shutdown_call_count += 1

        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            LifespanHooksRegistrationPluginConfig(
                on_startup_hooks=[
                    lambda _: async_on_startup_hook,
                    lambda _: sync_on_startup_hook,
                ],
                on_shutdown_hooks=[
                    lambda _: async_on_shutdown_hook,
                    lambda _: sync_on_shutdown_hook,
                ],
            ).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.send_local(message, {})
        async with app:
            await sleep(0)

        assert on_startup_call_count == 2
        assert on_shutdown_call_count == 2
