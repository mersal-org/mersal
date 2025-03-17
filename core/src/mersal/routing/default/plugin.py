from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mersal.plugins import Plugin
from mersal.routing import Router

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator
    from mersal.routing.default.config import DefaultRouterRegistrationConfig
    from mersal.routing.default.default_router import DefaultRouter

__all__ = ("DefaultRouterRegistrationPlugin",)


class DefaultRouterRegistrationPlugin(Plugin):
    def __init__(self, config: DefaultRouterRegistrationConfig) -> None:
        self._messages_destination_map = config.messages_destination_map

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_default_router(configurator: StandardConfigurator) -> Router:
            router = cast("DefaultRouter", configurator.get(Router))  # type: ignore[type-abstract]

            for destination, message_types in self._messages_destination_map.items():
                router.register(message_types, destination)

            return router

        configurator.decorate(Router, decorate_default_router)
