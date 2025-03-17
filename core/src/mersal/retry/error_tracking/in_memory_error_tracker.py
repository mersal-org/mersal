from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from .error_tracker import ErrorTracker

__all__ = ("InMemoryErrorTracker",)


class InMemoryErrorTracker(ErrorTracker):
    def __init__(self, maximum_failure_times: int) -> None:
        self.errors: dict[Any, list[Exception]] = defaultdict(list)
        self.maximum_failure_times = maximum_failure_times
        self.marked_as_final: set[Any] = set()

    async def register_error(self, message_id: Any, exception: Exception) -> None:
        self.errors[message_id].append(exception)

    async def clean_up(self, message_id: Any) -> None:
        self.errors.pop(message_id, None)

    async def has_failed_too_many_times(self, message_id: Any) -> bool:
        return message_id in self.marked_as_final or len(self.errors[message_id]) >= self.maximum_failure_times

    async def mark_as_final(self, message_id: Any) -> None:
        self.marked_as_final.add(message_id)

    async def get_exceptions(self, message_id: Any) -> Sequence[Exception]:
        return self.errors[message_id]
