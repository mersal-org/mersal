from collections.abc import Callable
from typing import Any

from mersal.configuration import StandardConfigurator
from mersal.plugins import Plugin

from .transport import Transport

__all__ = ("TransportDecoratorPlugin",)


class TransportDecoratorPlugin(Plugin):
    def __init__(
        self,
        transport_decorator_factory: Callable[[Transport], Transport],
    ) -> None:
        self.transport_decorator_factory = transport_decorator_factory

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_transport(configurator: StandardConfigurator) -> Any:
            return self.transport_decorator_factory(configurator.get(Transport))  # type: ignore[type-abstract]

        configurator.decorate(Transport, decorate_transport)
