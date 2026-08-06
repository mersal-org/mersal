import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.configuration import StandardConfigurator
from mersal.core.app import Mersal
from mersal.plugins import Plugin
from mersal.testing.core.test_doubles import LogicalMessageBuilder
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = ("TestSendOnlyIntegration",)


pytestmark = pytest.mark.anyio


class TestSendOnlyIntegration:
    async def test_send_only_defaults_to_false_and_creates_a_worker(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        plugins = [InMemoryTransportPluginConfig(network, "test-queue").plugin]

        app = Mersal("m", activator, plugins=plugins)

        assert app.configurator.send_only is False
        assert app.worker is not None

    async def test_send_only_is_exposed_on_the_configurator_and_skips_worker_creation(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        plugins = [InMemoryTransportPluginConfig(network, "test-queue").plugin]

        app = Mersal("m", activator, plugins=plugins, send_only=True)

        assert app.configurator.send_only is True
        assert app.worker is None

    async def test_send_only_app_can_still_start_stop_and_send(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        plugins = [InMemoryTransportPluginConfig(network, "test-queue").plugin]
        app = Mersal("m", activator, plugins=plugins, send_only=True)
        message = LogicalMessageBuilder.build()

        await app.start()
        await app.send_local(message, {})
        await app.stop()

        assert network.get_next("test-queue")

    async def test_plugins_can_read_send_only_while_registering(self):
        observed_values = []

        class ObservingPlugin(Plugin):
            def __call__(self, configurator: StandardConfigurator) -> None:
                observed_values.append(configurator.send_only)

        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
            ObservingPlugin(),
        ]

        Mersal("m", activator, plugins=plugins, send_only=True)

        assert observed_values == [True]
