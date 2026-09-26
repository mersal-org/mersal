from datetime import UTC, datetime, timedelta
from typing import Any

import anyio
import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.configuration.standard_configurator import InvalidConfigurationError
from mersal.core.app import Mersal
from mersal.exceptions import DeferralNotSupportedError
from mersal.messages import MessageHeaders
from mersal.persistence.in_memory import InMemoryTimeoutManager
from mersal.pipeline import MessageContext
from mersal.routing.default import DefaultRouterRegistrationConfig
from mersal.serialization.identity_serializer import IdentitySerializer
from mersal.testing.core.test_doubles.messages.logical_message_builder import DummyMessage
from mersal.testing.core.test_doubles.transport.transport_test_double import TransportTestDouble
from mersal.testing.core.transport.transport_decorator_helper import TransportDecoratorHelper
from mersal.timeouts import TimeoutsConfig
from mersal.transport.in_memory import InMemoryNetwork, InMemoryTransport, InMemoryTransportConfig
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal.transport.transport_bridge import TransportBridge
from mersal.transport.transport_decorator_plugin import TransportDecoratorPlugin

__all__ = (
    "TestDeferRouting",
    "TestDeferWithTimeoutManager",
)


pytestmark = pytest.mark.anyio


class NativeDeferralInMemoryTransport(InMemoryTransport):
    """Stands in for a transport that defers natively (e.g. RabbitMQ with a delayed exchange)."""

    @property
    def supports_deferral(self) -> bool:
        return True


def _headers(network: InMemoryNetwork, queue_address: str) -> MessageHeaders:
    message = network.get_next(queue_address)
    if message is None:
        raise AssertionError(f"no message in {queue_address}")
    return message.headers


def _app(network: InMemoryNetwork, queue_address: str = "test-queue", **kwargs: Any) -> Mersal:
    activator = kwargs.pop("activator", BuiltinHandlerActivator())
    plugins = [InMemoryTransportPluginConfig(network, queue_address).plugin, *kwargs.pop("plugins", [])]
    return Mersal("m", activator, plugins=plugins, **kwargs)


class TestDeferRouting:
    async def test_defer_local_goes_to_the_timeout_manager_with_defer_headers(self):
        network = InMemoryNetwork()
        app = _app(network, timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()))
        delay = timedelta(minutes=5)

        before = datetime.now(UTC)
        await app.defer_local(delay, DummyMessage())
        after = datetime.now(UTC)

        headers = _headers(network, "test-queue")
        deferred_until = headers.deferred_until
        assert deferred_until is not None
        assert before + delay <= deferred_until <= after + delay
        assert headers.deferred_recipient == "test-queue"

    async def test_defer_resolves_the_recipient_with_the_router(self):
        network = InMemoryNetwork()
        app = _app(
            network,
            timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()),
            default_router_registration=DefaultRouterRegistrationConfig({"owner": [DummyMessage]}),
        )

        await app.defer(timedelta(seconds=30), DummyMessage())

        assert _headers(network, "test-queue").deferred_recipient == "owner"
        assert network.get_next("owner") is None

    async def test_defer_to_explicit_address(self):
        network = InMemoryNetwork()
        app = _app(network, timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()))

        await app.defer(timedelta(seconds=30), DummyMessage(), address="other")

        assert _headers(network, "test-queue").deferred_recipient == "other"

    async def test_explicit_deferred_recipient_header_wins(self):
        network = InMemoryNetwork()
        app = _app(network, timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()))

        await app.defer_local(
            timedelta(seconds=30),
            DummyMessage(),
            headers={MessageHeaders.deferred_recipient_key: "elsewhere", "custom": "value"},
        )

        headers = _headers(network, "test-queue")
        assert headers.deferred_recipient == "elsewhere"
        assert headers["custom"] == "value"

    async def test_defer_goes_to_the_external_timeout_manager(self):
        network = InMemoryNetwork()
        app = _app(network, timeouts=TimeoutsConfig(external_timeout_manager_address="timeouts"))

        await app.defer(timedelta(seconds=30), DummyMessage(), address="other")

        assert _headers(network, "timeouts").deferred_recipient == "other"
        assert network.get_next("test-queue") is None

    async def test_native_deferral_sends_to_the_recipient_directly(self):
        network = InMemoryNetwork()
        transport = NativeDeferralInMemoryTransport(InMemoryTransportConfig(network, "test-queue"))
        app = Mersal(
            "m",
            BuiltinHandlerActivator(),
            transport=transport,
            serializer=IdentitySerializer(),
            timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()),
        )

        await app.defer(timedelta(seconds=30), DummyMessage(), address="other")

        headers = _headers(network, "other")
        assert headers.deferred_until is not None
        assert headers.deferred_recipient == "other"
        assert network.get_next("test-queue") is None

    async def test_raises_without_native_deferral_or_timeout_manager(self):
        transport = TransportTestDouble()
        app = Mersal("m", BuiltinHandlerActivator(), transport=transport, serializer=IdentitySerializer())

        with pytest.raises(DeferralNotSupportedError):
            await app.defer_local(timedelta(seconds=1), DummyMessage())
        with pytest.raises(DeferralNotSupportedError):
            await app.defer(timedelta(seconds=1), DummyMessage(), address="other")

        assert transport.sent_messages == []

    async def test_decorated_transport_reports_the_inner_transport_support(self):
        network = InMemoryNetwork()
        app = _app(
            network,
            plugins=[TransportDecoratorPlugin(TransportDecoratorHelper)],
        )
        app_with_native = Mersal(
            "m2",
            BuiltinHandlerActivator(),
            transport=NativeDeferralInMemoryTransport(InMemoryTransportConfig(network, "q2")),
            serializer=IdentitySerializer(),
            plugins=[TransportDecoratorPlugin(TransportDecoratorHelper)],
        )

        assert not app.transport.supports_deferral
        assert app_with_native.transport.supports_deferral

    async def test_transport_bridge_supports_deferral_only_if_all_its_transports_do(self):
        native = NativeDeferralInMemoryTransport(InMemoryTransportConfig(InMemoryNetwork(), "a"))

        assert TransportBridge(native, {"b": native}).supports_deferral
        assert not TransportBridge(native, {"b": TransportTestDouble()}).supports_deferral
        assert not TransportBridge(TransportTestDouble(), {}).supports_deferral


class TestDeferWithTimeoutManager:
    async def test_message_is_handled_once_due(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        received: list[MessageHeaders] = []

        def handler_factory(message_context: MessageContext, _: Mersal) -> Any:
            async def handler(message: DummyMessage) -> None:
                received.append(message_context.headers)

            return handler

        activator.register(DummyMessage, handler_factory)
        timeout_manager = InMemoryTimeoutManager()
        app = _app(
            network,
            activator=activator,
            timeouts=TimeoutsConfig(storage=timeout_manager, poll_interval=0.05),
        )

        await app.start()
        try:
            await app.defer_local(timedelta(milliseconds=400), DummyMessage())
            with anyio.fail_after(3):
                while not len(timeout_manager):
                    await anyio.sleep(0.01)
            assert received == []
            with anyio.fail_after(3):
                while not received:
                    await anyio.sleep(0.05)
        finally:
            await app.stop()

        assert len(timeout_manager) == 0
        assert MessageHeaders.deferred_until_key not in received[0]
        assert MessageHeaders.deferred_recipient_key not in received[0]

    async def test_external_timeout_manager_delivers_to_the_recipient(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        received: list[DummyMessage] = []

        def handler_factory(_: MessageContext, __: Mersal) -> Any:
            async def handler(message: DummyMessage) -> None:
                received.append(message)

            return handler

        activator.register(DummyMessage, handler_factory)
        timeout_manager = InMemoryTimeoutManager()
        timeouts_host = _app(
            network,
            "timeouts",
            timeouts=TimeoutsConfig(storage=timeout_manager, poll_interval=0.05),
        )
        sender = _app(
            network,
            "sender",
            send_only=True,
            timeouts=TimeoutsConfig(external_timeout_manager_address="timeouts"),
        )
        receiver = _app(network, "receiver", activator=activator)

        await timeouts_host.start()
        await receiver.start()
        try:
            await sender.defer(timedelta(milliseconds=300), DummyMessage(), address="receiver")
            with anyio.fail_after(3):
                while not received:
                    await anyio.sleep(0.05)
        finally:
            await receiver.stop()
            await timeouts_host.stop()

        assert len(timeout_manager) == 0

    async def test_receiving_a_deferred_message_without_a_timeout_manager_does_not_handle_it(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        received: list[DummyMessage] = []

        def handler_factory(_: MessageContext, __: Mersal) -> Any:
            async def handler(message: DummyMessage) -> None:
                received.append(message)

            return handler

        activator.register(DummyMessage, handler_factory)
        receiver = _app(network, "receiver", activator=activator)
        sender = _app(network, "sender", timeouts=TimeoutsConfig(external_timeout_manager_address="receiver"))

        await receiver.start()
        try:
            await sender.defer(timedelta(milliseconds=1), DummyMessage(), address="receiver")
            with anyio.fail_after(3):
                while network.queue_count("error") == 0:
                    await anyio.sleep(0.05)
        finally:
            await receiver.stop()

        assert received == []

    async def test_send_only_app_cannot_host_a_timeout_manager(self):
        with pytest.raises(InvalidConfigurationError):
            _app(InMemoryNetwork(), send_only=True, timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()))

    @pytest.mark.parametrize(
        "kwargs",
        [{}, {"storage": InMemoryTimeoutManager(), "external_timeout_manager_address": "timeouts"}],
    )
    async def test_config_needs_exactly_one_of_storage_and_external_address(self, kwargs: dict[str, Any]):
        with pytest.raises(InvalidConfigurationError):
            TimeoutsConfig(**kwargs)
