from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from mersal.configuration.standard_configurator import InvalidConfigurationError
from mersal.lifespan.lifespan_hooks_registration_plugin import (
    LifespanHooksRegistrationPluginConfig,
)
from mersal.logging import Logger
from mersal.plugins import Plugin
from mersal.threading.anyio.anyio_periodic_async_task_factory import (
    AnyIOPeriodicTaskFactory,
)
from mersal.timeouts.due_messages_sender import DueMessagesSender
from mersal.timeouts.timeout_manager import TimeoutManager
from mersal.transport import Transport
from mersal.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator
    from mersal.timeouts.config import TimeoutsConfig
    from mersal.types import LifespanHook

__all__ = ("TimeoutsPlugin",)


class TimeoutsPlugin(Plugin):
    def __init__(self, config: TimeoutsConfig):
        self._config = config

    def __call__(self, configurator: StandardConfigurator) -> None:
        from mersal.timeouts.config import TimeoutsConfig

        configurator.register(TimeoutsConfig, lambda _: self._config)

        storage = self._config.storage
        if storage is None:
            return

        if configurator.send_only:
            raise InvalidConfigurationError(
                "A send-only app can't host a timeout manager since it never receives the deferred "
                "messages sent to it; use TimeoutsConfig(external_timeout_manager_address=...) instead"
            )

        def register_sender(configurator: StandardConfigurator) -> DueMessagesSender:
            logger = configurator.get(Logger)  # type: ignore[type-abstract]
            return DueMessagesSender(
                AnyIOPeriodicTaskFactory(logger=logger),
                configurator.get(Transport),  # type: ignore[type-abstract]
                configurator.get(TimeoutManager),  # type: ignore[type-abstract]
                logger=logger,
                poll_interval=self._config.poll_interval,
            )

        configurator.register(TimeoutManager, lambda _: storage)
        configurator.register(DueMessagesSender, register_sender)

        startup_hooks: list[Callable[[StandardConfigurator], LifespanHook]] = [
            lambda config: AsyncCallable(config.get(TimeoutManager)),  # type: ignore[type-abstract]
            lambda config: AsyncCallable(config.get(DueMessagesSender).start),
        ]
        shutdown_hooks: list[Callable[[StandardConfigurator], LifespanHook]] = [
            lambda config: AsyncCallable(config.get(DueMessagesSender).stop),
        ]
        LifespanHooksRegistrationPluginConfig(
            on_startup_hooks=startup_hooks,
            on_shutdown_hooks=shutdown_hooks,
        ).plugin(configurator)
