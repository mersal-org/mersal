from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.di import Provide
from litestar.plugins import InitPluginProtocol

from mersal.app import Mersal  # noqa: TC001

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


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
            dependencies: dict[str, Provide] = {}
            for k, v in self._config.app_instances.items():

                def provide_app(app: Mersal = v) -> Mersal:
                    return app

                dependencies[k] = Provide(provide_app, sync_to_thread=False)
            app_config.dependencies.update(**dependencies)

        return app_config
