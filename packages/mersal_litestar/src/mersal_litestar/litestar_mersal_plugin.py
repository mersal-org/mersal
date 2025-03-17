from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.di import Provide
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from mersal.app import Mersal

__all__ = (
    "LitestarMersalPlugin",
    "LitestarMersalPluginConfig",
)


@dataclass
class LitestarMersalPluginConfig:
    app_instances: dict[str, Mersal]
    inject_instances: bool = True

    @property
    def plugin(self) -> LitestarMersalPlugin:
        return LitestarMersalPlugin(self)


class LitestarMersalPlugin(InitPluginProtocol):
    def __init__(self, config: LitestarMersalPluginConfig) -> None:
        self._config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.lifespan.extend(self._config.app_instances.values())
        if self._config.inject_instances:
            app_config.dependencies.update(
                **{k: Provide(lambda v=v: v, sync_to_thread=False) for k, v in self._config.app_instances.items()}
            )

        return app_config
