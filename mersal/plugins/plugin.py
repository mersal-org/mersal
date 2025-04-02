from typing import Protocol

from mersal.configuration import StandardConfigurator

__all__ = ("Plugin",)


class Plugin(Protocol):
    def __call__(self, configurator: StandardConfigurator) -> None: ...
