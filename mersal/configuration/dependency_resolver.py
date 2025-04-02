from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar, cast

__all__ = ("DependencyResolver", "DependencyT", "Resolver")


DependencyT = TypeVar("DependencyT")
Resolver: TypeAlias = Callable[["DependencyResolver"], Any]


class DependencyResolver:
    def __init__(self) -> None:
        self._register_resolvers: dict[type, Resolver] = {}
        self._decorate_resolvers: dict[type, list[Resolver]] = defaultdict(list)
        self._temp_instances: dict[type, Any] = {}
        self._final_instances: dict[type, Any] = {}
        self._is_running_decorators: dict[type, bool] = defaultdict(lambda: False)

    def register(self, depedency_type: type, resolver: Resolver) -> None:
        self._register_resolvers[depedency_type] = resolver

    def decorate(self, depedency_type: type, resolver: Resolver) -> None:
        self._decorate_resolvers[depedency_type].append(resolver)

    def has_registration_resolver(self, dependency_type: type) -> bool:
        return self._register_resolvers.get(dependency_type) is not None

    def resolve_remaining(self) -> None:
        for _type in self._register_resolvers:
            if _type not in self._final_instances:
                self[_type]

    def __getitem__(self, dependency_type: type[DependencyT]) -> DependencyT:
        if _instance := self._final_instances.get(dependency_type):
            return cast("DependencyT", _instance)

        if self._is_running_decorators.get(dependency_type) and (
            _instance := self._temp_instances.get(dependency_type)
        ):
            return cast("DependencyT", _instance)

        resolver = self._register_resolvers[dependency_type]
        instance = resolver(self)
        self._temp_instances[dependency_type] = instance

        self._is_running_decorators[dependency_type] = True
        for decorator in self._decorate_resolvers[dependency_type]:
            instance = decorator(self)
            self._temp_instances[dependency_type] = instance
        self._is_running_decorators[dependency_type] = False

        del self._temp_instances[dependency_type]
        self._final_instances[dependency_type] = instance
        return cast("DependencyT", instance)
