from typing import Any

from mersal.configuration import StandardConfigurator
from mersal.plugins.plugin import Plugin

__all__ = ("generic_registration_plugin",)


def generic_registration_plugin(instance: Any, instance_type: type) -> Plugin:
    def register(configurator: StandardConfigurator) -> None:
        configurator.register(instance_type, lambda _: instance)

    return register
