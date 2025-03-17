from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mersal.lifespan import LifespanHandler
from mersal.plugins import Plugin

if TYPE_CHECKING:
    from collections.abc import Callable

    from mersal.configuration import StandardConfigurator
    from mersal.types import LifespanHook


__all__ = (
    "LifespanHooksRegistrationPlugin",
    "LifespanHooksRegistrationPluginConfig",
)


@dataclass
class LifespanHooksRegistrationPluginConfig:
    on_startup_hooks: list[Callable[[StandardConfigurator], LifespanHook]] = field(default_factory=list)
    on_shutdown_hooks: list[Callable[[StandardConfigurator], LifespanHook]] = field(default_factory=list)

    @property
    def plugin(self) -> LifespanHooksRegistrationPlugin:
        return LifespanHooksRegistrationPlugin(self)


class LifespanHooksRegistrationPlugin(Plugin):
    def __init__(self, config: LifespanHooksRegistrationPluginConfig) -> None:
        self._on_startup_hooks = config.on_startup_hooks
        self._on_shutdown_hooks = config.on_shutdown_hooks

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_lifespan_handler(configurator: StandardConfigurator) -> Any:
            lifespan_handler: LifespanHandler = configurator.get(LifespanHandler)  # type: ignore[type-abstract]

            for h in self._on_startup_hooks:
                lifespan_handler.register_on_startup_hook(h(configurator))
            for h in self._on_shutdown_hooks:
                lifespan_handler.register_on_shutdown_hook(h(configurator))

            return lifespan_handler

        configurator.decorate(LifespanHandler, decorate_lifespan_handler)
