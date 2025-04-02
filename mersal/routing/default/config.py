from collections.abc import Iterable
from dataclasses import dataclass

from mersal.routing.default.plugin import DefaultRouterRegistrationPlugin

__all__ = ("DefaultRouterRegistrationConfig",)


@dataclass
class DefaultRouterRegistrationConfig:
    messages_destination_map: dict[str, Iterable[type]]

    @property
    def plugin(self) -> DefaultRouterRegistrationPlugin:
        return DefaultRouterRegistrationPlugin(self)
