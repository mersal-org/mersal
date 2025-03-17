from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mersal.lifespan import LifespanHandler
from mersal.plugins import Plugin

if TYPE_CHECKING:
    from mersal.app import Mersal
    from mersal.configuration import StandardConfigurator
    from mersal.types import LifespanHook

__all__ = (
    "AutosubscribeConfig",
    "AutosubscribePlugin",
)


@dataclass
class AutosubscribeConfig:
    events: set[Any] = field(default_factory=set)

    @property
    def plugin(self) -> AutosubscribePlugin:
        return AutosubscribePlugin(self)


class AutosubscribePlugin(Plugin):
    def __init__(self, config: AutosubscribeConfig) -> None:
        self._events = config.events

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate(configurator: StandardConfigurator) -> Any:
            lifespan_handler: LifespanHandler = configurator.get(LifespanHandler)  # type: ignore[type-abstract]
            app: Mersal = configurator.mersal

            lifespan_handler.register_on_startup_hook(self._subscribe(app))

            return lifespan_handler

        configurator.decorate(LifespanHandler, decorate)

    def _subscribe(self, app: Mersal) -> LifespanHook:
        events = deepcopy(self._events)

        async def subscribe(
            events: set[Any] = events,
        ) -> None:
            for e in events:
                await app.subscribe(e)

        return subscribe
