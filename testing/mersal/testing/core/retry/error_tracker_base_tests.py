from typing import Any, Protocol
from uuid import uuid4

import pytest

from mersal.retry import ErrorTracker

__all__ = (
    "ErrorTrackerBaseTests",
    "ErrorTrackerMaker",
)


pytestmark = pytest.mark.anyio


class ErrorTrackerMaker(Protocol):
    def __call__(self, **kwargs: Any) -> ErrorTracker: ...


class ErrorTrackerBaseTests:
    @pytest.fixture
    def error_tracker_maker(self) -> ErrorTrackerMaker:
        def maker(**kwargs: Any) -> ErrorTracker:
            raise NotImplementedError()

        return maker

    async def test_returns_no_errors(self, error_tracker_maker: ErrorTrackerMaker) -> None:
        subject = error_tracker_maker()
        assert not await subject.get_exceptions(uuid4())

    async def test_track_errors(self, error_tracker_maker: ErrorTrackerMaker) -> None:
        subject = error_tracker_maker()

        m1 = uuid4()
        m2 = uuid4()
        e1 = Exception()
        e2 = Exception()
        e3 = Exception()
        await subject.register_error(m1, e1)
        await subject.register_error(m1, e2)
        await subject.register_error(m2, e3)

        assert len(await subject.get_exceptions(m1)) == 2
        assert len(await subject.get_exceptions(m2)) == 1

    async def test_has_failed_too_many_times(self, error_tracker_maker: ErrorTrackerMaker) -> None:
        subject = error_tracker_maker(maximum_failure_times=3)
        m1 = uuid4()
        m2 = uuid4()
        m3 = uuid4()
        m4 = uuid4()
        data = [(m1, 1), (m2, 3), (m3, 4), (m4, 2)]
        for d in data:
            for _ in range(d[1]):
                await subject.register_error(d[0], Exception())

        assert not await subject.has_failed_too_many_times(m1)
        assert not await subject.has_failed_too_many_times(m4)
        assert await subject.has_failed_too_many_times(m2)
        assert await subject.has_failed_too_many_times(m3)

    async def test_clean_up(self, error_tracker_maker: ErrorTrackerMaker) -> None:
        subject = error_tracker_maker()
        m1 = uuid4()
        m2 = uuid4()
        e1 = Exception()
        e2 = Exception()
        e3 = Exception()
        await subject.register_error(m1, e1)
        await subject.register_error(m1, e2)
        await subject.register_error(m2, e3)

        await subject.clean_up(m1)

        assert not await subject.get_exceptions(m1)
        assert await subject.get_exceptions(m2)

    async def test_mark_as_final(self, error_tracker_maker: ErrorTrackerMaker) -> None:
        subject = error_tracker_maker(maximum_failure_times=10)
        m1 = uuid4()
        e1 = Exception()
        await subject.register_error(m1, e1)

        await subject.mark_as_final(m1)

        assert len(await subject.get_exceptions(m1)) == 1
        assert await subject.has_failed_too_many_times(m1)
