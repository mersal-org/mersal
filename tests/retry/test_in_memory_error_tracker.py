from uuid import uuid4

import pytest

from mersal.retry import InMemoryErrorTracker
from mersal.testing.core.retry.error_tracker_base_tests import (
    ErrorTrackerBaseTests,
    ErrorTrackerMaker,
)

__all__ = ("TestInMemoryErrorTracker",)


pytestmark = pytest.mark.anyio


class _LoggerSpy:
    def __init__(self) -> None:
        self.debug_calls: list[tuple[str, dict]] = []

    def debug(self, event, **kwargs):
        self.debug_calls.append((event, kwargs))

    def info(self, event, **kwargs):
        pass

    def warning(self, event, **kwargs):
        pass

    def exception(self, event, **kwargs):
        pass


class TestInMemoryErrorTracker(ErrorTrackerBaseTests):
    @pytest.fixture
    def error_tracker_maker(self) -> ErrorTrackerMaker:
        def maker(**kwargs):
            data = {}
            d = kwargs.get("maximum_failure_times")
            if d:
                data["maximum_failure_times"] = d
            else:
                data["maximum_failure_times"] = 2

            return InMemoryErrorTracker(**data)

        return maker

    async def test_logs_before_cleaning_up(self):
        logger = _LoggerSpy()
        subject = InMemoryErrorTracker(maximum_failure_times=2, logger=logger)  # type: ignore
        message_id = uuid4()
        await subject.register_error(message_id, Exception())
        await subject.register_error(message_id, Exception())

        await subject.clean_up(message_id)

        assert logger.debug_calls == [
            ("error_tracker.clean_up", {"message_id": message_id, "number_of_tracked_errors": 2}),
        ]
        assert not await subject.get_exceptions(message_id)

    async def test_sweep_evicts_entries_older_than_max_age(self, monkeypatch):
        subject = InMemoryErrorTracker(maximum_failure_times=10, max_age_seconds=60.0)
        m1 = uuid4()
        m2 = uuid4()

        clock = [1_000.0]
        monkeypatch.setattr("mersal.retry.error_tracking.in_memory_error_tracker.time.monotonic", lambda: clock[0])

        await subject.register_error(m1, Exception())
        await subject.mark_as_final(m1)
        clock[0] += 30.0
        await subject.register_error(m2, Exception())

        # m1's last error is now 90s old (> max_age=60s), m2's is fresh.
        clock[0] += 60.0
        await subject._sweep()

        assert not await subject.get_exceptions(m1)
        assert not await subject.has_failed_too_many_times(m1)
        assert len(await subject.get_exceptions(m2)) == 1

    async def test_sweep_is_noop_without_max_age_configured(self):
        subject = InMemoryErrorTracker(maximum_failure_times=10)
        message_id = uuid4()
        await subject.register_error(message_id, Exception())

        await subject.start()
        await subject.stop()

        assert len(await subject.get_exceptions(message_id)) == 1
