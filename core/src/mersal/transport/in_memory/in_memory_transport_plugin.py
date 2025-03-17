from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mersal.plugins import Plugin
from mersal.serialization import Serializer
from mersal.serialization.identity_serializer import IdentitySerializer
from mersal.transport.transport import Transport

from .in_memory_transport import InMemoryTransportConfig

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator

__all__ = (
    "InMemoryTransportPlugin",
    "InMemoryTransportPluginConfig",
)


@dataclass
class InMemoryTransportPluginConfig(InMemoryTransportConfig):
    use_cool_serializer: bool = True

    @property
    def plugin(self) -> InMemoryTransportPlugin:
        return InMemoryTransportPlugin(self)


class InMemoryTransportPlugin(Plugin):
    def __init__(
        self,
        config: InMemoryTransportPluginConfig,
    ) -> None:
        self._config = config
        self.use_identity_serializer = config.use_cool_serializer

    def __call__(self, configurator: StandardConfigurator) -> None:
        def register_in_memory_transport(_: StandardConfigurator) -> Any:
            return self._config.transport

        configurator.register(Transport, register_in_memory_transport)

        def register_cool_serializer(_: StandardConfigurator) -> Any:
            return IdentitySerializer()

        if self.use_identity_serializer:
            configurator.register(Serializer, register_cool_serializer)
