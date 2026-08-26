import time
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from mersal.logging import Logger, NullLogger
from mersal.threading import PeriodicAsyncTask, PeriodicAsyncTaskFactory

from .error_tracker import ErrorTracker

__all__ = ("InMemoryErrorTracker",)


class InMemoryErrorTracker(ErrorTracker):
    def __init__(
        self,
        maximum_failure_times: int,
        logger: Logger | None = None,
        periodic_task_factory: PeriodicAsyncTaskFactory | None = None,
        max_age_seconds: float | None = None,
        sweep_interval_seconds: float = 60.0,
    ) -> None:
        """Initialize ``InMemoryErrorTracker``.

        Args:
            maximum_failure_times: Number of registered errors after which a message is
                                  considered poisonous.
            logger: Logger instance.
            periodic_task_factory: Creates the background sweep task. Required (along with
                                  `max_age_seconds`) for the age-based sweep to run at all -
                                  `start`/`stop` are no-ops without it, so tracker instances
                                  built for tests without a running event loop stay safe.
            max_age_seconds: Evict a message's tracked errors once this long has passed
                            since its last registered error, regardless of whether
                            `clean_up` was ever called for it - a safety net against
                            entries orphaned by a missed cleanup call site (see
                            `RetryStrategySettings.error_tracking_max_age_seconds`).
                            `None` disables the sweep.
            sweep_interval_seconds: How often to check for stale entries.
        """
        self.errors: dict[Any, list[Exception]] = defaultdict(list)
        self.maximum_failure_times = maximum_failure_times
        self.marked_as_final: set[Any] = set()
        self.logger = logger if logger is not None else NullLogger()
        self._last_error_at: dict[Any, float] = {}
        self._max_age_seconds = max_age_seconds
        self._sweep_task: PeriodicAsyncTask | None = (
            periodic_task_factory("ErrorTracker-Sweep", self._sweep, sweep_interval_seconds)
            if periodic_task_factory is not None and max_age_seconds is not None
            else None
        )

    async def start(self) -> None:
        if self._sweep_task is not None:
            await self._sweep_task.start()

    async def stop(self) -> None:
        if self._sweep_task is not None:
            await self._sweep_task.stop()

    async def register_error(self, message_id: Any, exception: Exception) -> None:
        self.errors[message_id].append(exception)
        self._last_error_at[message_id] = time.monotonic()

    async def clean_up(self, message_id: Any) -> None:
        self.logger.debug(
            "error_tracker.clean_up",
            message_id=message_id,
            number_of_tracked_errors=len(self.errors.get(message_id, [])),
        )
        self.errors.pop(message_id, None)
        self.marked_as_final.discard(message_id)
        self._last_error_at.pop(message_id, None)

    async def has_failed_too_many_times(self, message_id: Any) -> bool:
        return message_id in self.marked_as_final or len(self.errors[message_id]) >= self.maximum_failure_times

    async def mark_as_final(self, message_id: Any) -> None:
        self.marked_as_final.add(message_id)

    async def get_exceptions(self, message_id: Any) -> Sequence[Exception]:
        return self.errors[message_id]

    async def _sweep(self) -> None:
        assert self._max_age_seconds is not None
        now = time.monotonic()
        stale_ids = [
            message_id
            for message_id, last_error_at in self._last_error_at.items()
            if now - last_error_at > self._max_age_seconds
        ]
        for message_id in stale_ids:
            self.logger.warning(
                "error_tracker.sweep.evict",
                message_id=message_id,
                number_of_tracked_errors=len(self.errors.get(message_id, [])),
            )
            await self.clean_up(message_id)
