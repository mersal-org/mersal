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
