import uuid
from typing import Any

import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.configuration import StandardConfigurator
from mersal.core.app import Mersal
from mersal.lifespan.autosubscribe import AutosubscribeConfig
from mersal.logging import Logger
from mersal.outbox.config import OutboxConfig
from mersal.outbox.outbox_forwarder import OutboxForwarder
from mersal.outbox.plugin import OutboxPlugin
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.persistence.in_memory.in_memory_saga_storage import InMemorySagaStorage
from mersal.plugins import Plugin, generic_registration_plugin
from mersal.sagas import SagaConfig
from mersal.sagas.plugin import SagaPlugin
from mersal.testing.core.test_doubles import LogicalMessageBuilder
from mersal.testing.core.test_doubles.outbox.outbox_storage_test_double import (
    OutboxStorageTestDouble,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = ("TestSendOnlyIntegration",)


class SomeAutosubscribeEvent:
    pass


class LoggerSpy:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def debug(self, event: str, **kwargs: Any) -> None:
        self.records.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.records.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.records.append(("warning", event, kwargs))

    def warn(self, event: str, **kwargs: Any) -> None:
        self.records.append(("warn", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.records.append(("error", event, kwargs))

    def fatal(self, event: str, **kwargs: Any) -> None:
        self.records.append(("fatal", event, kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self.records.append(("exception", event, kwargs))

    def critical(self, event: str, **kwargs: Any) -> None:
        self.records.append(("critical", event, kwargs))

    def set_level(self, level: int) -> None: ...

    def bind(self, **kwargs: Any) -> "LoggerSpy":
        return self

    def unbind(self, *keys: str) -> "LoggerSpy":
        return self

    def new(self, **kwargs: Any) -> "LoggerSpy":
        return self


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

    async def test_send_only_skips_outbox_storage_init_and_forwarder(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        outbox_storage = OutboxStorageTestDouble()
        logger_spy = LoggerSpy()
        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
            generic_registration_plugin(logger_spy, Logger),
            OutboxPlugin(OutboxConfig(storage=outbox_storage)),
        ]

        app = Mersal("m", activator, plugins=plugins, send_only=True)
        assert not app.configurator.is_registered(OutboxForwarder)

        await app.start()
        await app.stop()

        assert any(level == "info" and event == "outbox.send_only.skip" for level, event, _ in logger_spy.records)

    async def test_send_only_still_forwards_outbox_when_not_send_only(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        outbox_storage = OutboxStorageTestDouble()
        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
            OutboxPlugin(OutboxConfig(storage=outbox_storage)),
        ]

        app = Mersal("m", activator, plugins=plugins, send_only=False)

        assert app.configurator.is_registered(OutboxForwarder)

    async def test_send_only_skips_saga_storage_init(self):
        activator = BuiltinHandlerActivator()
        saga_storage = InMemorySagaStorage()
        logger_spy = LoggerSpy()
        network = InMemoryNetwork()
        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
            generic_registration_plugin(logger_spy, Logger),
            SagaPlugin(SagaConfig(storage=saga_storage)),
        ]

        app = Mersal("m", activator, plugins=plugins, send_only=True)
        sentinel_id = uuid.uuid4()
        saga_storage._store[sentinel_id] = "not-cleared"  # type: ignore[assignment]

        await app.start()
        await app.stop()

        assert saga_storage._store.get(sentinel_id) == "not-cleared"
        assert any(event == "saga.send_only.skip" for _, event, _ in logger_spy.records)

    async def test_send_only_skips_autosubscribe(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        store = InMemorySubscriptionStore()
        logger_spy = LoggerSpy()
        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
            generic_registration_plugin(logger_spy, Logger),
        ]

        app = Mersal(
            "m",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(store),
            autosubscribe=AutosubscribeConfig(events={SomeAutosubscribeEvent}),
            send_only=True,
        )

        await app.start()
        await app.stop()

        assert len(store) == 0
        assert any(event == "autosubscribe.send_only.skip" for _, event, _ in logger_spy.records)
