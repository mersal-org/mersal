from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from mersal.transport import Transport

from .dependency_resolver import DependencyResolver, Resolver

DependencyT = TypeVar("DependencyT")


class InvalidConfigurationError(Exception):
    pass


if TYPE_CHECKING:
    from mersal.app import Mersal

__all__ = (
    "InvalidConfigurationError",
    "StandardConfigurator",
)


ConfigurationCallback = Callable[["StandardConfigurator"], None]
StandardConfiguratorResolver: TypeAlias = Callable[["StandardConfigurator"], Any]


class StandardConfigurator:
    def __init__(self) -> None:
        self.mersal: Mersal
        self._dependecy_resolver = DependencyResolver()

    def register(self, dependency_type: type, resolver: StandardConfiguratorResolver) -> None:
        def _resolver_wrapper(dependendency_resolver: DependencyResolver) -> Any:
            return resolver(self)

        self._dependecy_resolver.register(dependency_type, _resolver_wrapper)

    def decorate(self, dependency_type: type, resolver: StandardConfiguratorResolver) -> None:
        def _resolver_wrapper(dependendency_resolver: DependencyResolver) -> Any:
            return resolver(self)

        self._dependecy_resolver.decorate(dependency_type, _resolver_wrapper)

    def get(self, dependency_type: type[DependencyT]) -> DependencyT:
        return self._dependecy_resolver[dependency_type]

    def get_optional(self, dependency_type: type[DependencyT]) -> DependencyT | None:
        try:
            return self._dependecy_resolver[dependency_type]
        except KeyError:
            return None

    def resolve(self) -> None:
        self._assert_transport()
        self._dependecy_resolver.resolve_remaining()

    def is_registered(self, dependency_type: type) -> bool:
        return self._dependecy_resolver.has_registration_resolver(dependency_type)

    def _register_default_dependency_if_needed(self, dependency_type: type, resolver: Resolver) -> None:
        if not self.is_registered(dependency_type):
            self._dependecy_resolver.register(dependency_type, resolver)

    def _assert_transport(self) -> None:
        if not self.is_registered(Transport):
            raise InvalidConfigurationError("Transport not configured.")
