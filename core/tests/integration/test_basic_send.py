import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.transport import (
    AmbientContext,
    DefaultTransactionContext,
    DefaultTransactionContextWithOwningApp,
    Transport,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal.transport.transport_decorator_plugin import TransportDecoratorPlugin
from mersal_testing.test_doubles import LogicalMessageBuilder
from mersal_testing.transport.transport_decorator_helper import (
    TransportDecoratorHelper,
)

__all__ = ("TestBasicSendIntegration",)


pytestmark = pytest.mark.anyio


class TestBasicSendIntegration:
    async def test_sending(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        plugins = [InMemoryTransportPluginConfig(network, queue_address).plugin]
        app = Mersal("m", activator, plugins=plugins)
        message = LogicalMessageBuilder.build()

        await app.send_local(message, {})

        assert network.get_next(queue_address)

    async def test_with_incorrect_app_in_ambient_context(self):
        transport_decorator: TransportDecoratorHelper | None = None

        def transport_decorator_factory(transport: Transport):
            nonlocal transport_decorator
            if transport_decorator:
                return transport_decorator
            transport_decorator = TransportDecoratorHelper(transport)
            return transport_decorator

        transport_decorator_plugin = TransportDecoratorPlugin(transport_decorator_factory)

        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            transport_decorator_plugin,
        ]
        plugins2 = [
            InMemoryTransportPluginConfig(network, "q2").plugin,
            transport_decorator_plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        app2 = Mersal("m2", activator, plugins=plugins2)
        message = LogicalMessageBuilder.build()

        random_transaction_context = DefaultTransactionContext()
        AmbientContext().current = random_transaction_context
        await app.send_local(message, {})

        assert transport_decorator
        assert transport_decorator._sent[0][2] is not random_transaction_context

        random_transaction_context2 = DefaultTransactionContextWithOwningApp(app2)
        AmbientContext().current = random_transaction_context2
        await app.send_local(message, {})

        assert transport_decorator._sent[1][2] is not random_transaction_context2

        random_transaction_context3 = DefaultTransactionContextWithOwningApp(app)
        AmbientContext().current = random_transaction_context3
        await app.send_local(message, {})

        assert transport_decorator._sent[2][2] is random_transaction_context3

    async def test_send_uses_the_correct_transaction_context(self):
        transport_decorator: TransportDecoratorHelper | None = None

        def transport_decorator_factory(transport: Transport):
            nonlocal transport_decorator
            if transport_decorator:
                return transport_decorator
            transport_decorator = TransportDecoratorHelper(transport)
            return transport_decorator

        transport_decorator_plugin = TransportDecoratorPlugin(transport_decorator_factory)

        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            transport_decorator_plugin,
        ]
        app = Mersal("m", activator, plugins=plugins)
        message = LogicalMessageBuilder.build()

        await app.send_local(message, {})

        assert transport_decorator
        AmbientContext().current = transport_decorator._sent[0][2]

        await app.send_local(message, {})

        assert transport_decorator._sent[1][2] is transport_decorator._sent[0][2]
