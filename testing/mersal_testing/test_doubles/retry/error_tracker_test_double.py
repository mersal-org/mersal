import uuid
from collections.abc import Sequence
from copy import deepcopy

from mersal.retry import InMemoryErrorTracker

__all__ = ("ErrorTrackerTestTouble",)


class ErrorTrackerTestTouble(InMemoryErrorTracker):
    def __init__(self, maximum_failure_times: int = 5) -> None:
        super().__init__(maximum_failure_times=maximum_failure_times)

    async def register_error(self, message_id: uuid.UUID, exception: Exception) -> None:
        await super().register_error(message_id, exception)
        self._registered_errors_spy = deepcopy(self.errors)

    async def clean_up(self, message_id: uuid.UUID) -> None:
        pass

    async def has_failed_too_many_times(self, message_id: uuid.UUID) -> bool:
        return await super().has_failed_too_many_times(message_id)

    async def mark_as_final(self, message_id: uuid.UUID) -> None:
        await super().mark_as_final(message_id)

    async def get_exceptions(self, message_id: uuid.UUID) -> Sequence[Exception]:
        return await super().get_exceptions(message_id)
