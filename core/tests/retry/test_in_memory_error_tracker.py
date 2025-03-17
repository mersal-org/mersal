import pytest

from mersal.retry import InMemoryErrorTracker
from mersal_testing.retry.error_tracker_base_tests import (
    ErrorTrackerBaseTests,
    ErrorTrackerMaker,
)

__all__ = ("TestInMemoryErrorTracker",)


pytestmark = pytest.mark.anyio


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
