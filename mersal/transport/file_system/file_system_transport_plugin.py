from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mersal.lifespan.lifespan_hooks_registration_plugin import LifespanHooksRegistrationPluginConfig
from mersal.plugins import Plugin
from mersal.transport.transport import Transport
from mersal.utils.sync import AsyncCallable

from .file_system_transport import FileSystemTransportConfig

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator

__all__ = (
    "FileSystemTransportPlugin",
    "FileSystemTransportPluginConfig",
)


@dataclass
class FileSystemTransportPluginConfig(FileSystemTransportConfig):
    @property
    def plugin(self) -> FileSystemTransportPlugin:
        return FileSystemTransportPlugin(self)


class FileSystemTransportPlugin(Plugin):
    def __init__(
        self,
        config: FileSystemTransportPluginConfig,
    ) -> None:
        self._config = config

    def __call__(self, configurator: StandardConfigurator) -> None:
        def register_file_system_transport(_: StandardConfigurator) -> Any:
            return self._config.transport

        configurator.register(Transport, register_file_system_transport)

        startup_hooks = [
            lambda config: AsyncCallable(self._config.transport),
        ]
        plugin = LifespanHooksRegistrationPluginConfig(
            on_startup_hooks=startup_hooks,  # type: ignore[arg-type]
        ).plugin
        plugin(configurator)
