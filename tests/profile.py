import anyio

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.app_runner_helper import AppRunnerHelper

__all__ = (
    "DummyMessage",
    "DummyMessageHandler",
    "main",
)


class DummyMessage:
    pass


class DummyMessageHandler:
    async def __call__(self, message: DummyMessage):
        pass


async def main():
    network = InMemoryNetwork()
    queue_address = "test-queue"
    activator = BuiltinHandlerActivator()
    message = DummyMessage()
    activator.register(DummyMessage, lambda m, b: DummyMessageHandler())
    plugins = [InMemoryTransportPluginConfig(network, queue_address).plugin]
    app = Mersal("m1", activator, plugins=plugins)
    app_runner = AppRunnerHelper(app)
    await app_runner.run()
    for _ in range(100000):
        await app.send_local(message, {})

    await app_runner.stop()


if __name__ == "__main__":
    anyio.run(main)
