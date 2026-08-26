from typing import Any, TypeVar, cast

__all__ = ("StepContext",)


T = TypeVar("T")

STEP_EXECUTION_COUNT_KEY = "step_execution_count"
RETRY_ATTEMPTS_KEY = "retry_attempts"


class StepContext:
    step_context_key = "step_context"

    def __init__(self) -> None:
        self._items: dict[type, Any] = {}
        self._items_keys: dict[str, Any] = {}

    def save(self, instance: Any, instance_type: type | None = None) -> None:
        _type = instance_type if instance_type else type(instance)
        self._items[_type] = instance

    def save_keys(self, key: str, value: Any) -> None:
        self._items_keys[key] = value

    def load(self, instance_type: type[T]) -> T:
        # Actually returns None when instance_type was never saved; callers that may hit
        # that case are expected to falsy-check the result despite the non-Optional type.
        return cast("T", self._items.get(instance_type))

    def load_keys(self, key: str) -> Any:
        return self._items_keys.get(key)
