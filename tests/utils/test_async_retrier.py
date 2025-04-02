import time
from math import isclose
from typing import Protocol

import pytest

from mersal.utils import AsyncRetrier
from mersal_testing.counter import Counter, FailingCounter

__all__ = (
    "AsyncRetrierMaker",
    "TestAsyncRetrier",
    "subject_maker",
)


pytestmark = pytest.mark.anyio


class AsyncRetrierMaker(Protocol):
    def __call__(self, delays: list[float] | None = None) -> AsyncRetrier: ...


@pytest.fixture
def subject_maker() -> AsyncRetrierMaker:
    def maker(delays: list[float] | None = None) -> AsyncRetrier:
        return AsyncRetrier(delays=delays if delays is not None else [])

    return maker


class TestAsyncRetrier:
    async def test_returns_after_successfull_invocation(self, subject_maker: AsyncRetrierMaker):
        counter = Counter()
        subject = subject_maker(delays=[0.1])

        t0 = time.time()
        await subject.run(counter.task)
        t1 = time.time()
        assert (t1 - t0) < 0.1

        assert counter.total == 1

    async def test_delays_after_multiple_failed_invocations(self, subject_maker: AsyncRetrierMaker):
        counter = FailingCounter(fail_at_call=[1, 2])
        subject = subject_maker(delays=[0.1, 0.2, 1])

        t0 = time.time()
        await subject.run(counter.task)

        t1 = time.time()
        assert isclose(t1 - t0, 0.3, abs_tol=1e-01)
        assert counter.calls == 3
        assert counter.total == 1

    async def test_raises_exception_after_exhausting_retries(self, subject_maker: AsyncRetrierMaker):
        counter = FailingCounter(fail_at_call=[1, 2, 3, 4])
        subject = subject_maker(delays=[0.1, 0.2, 0.3])

        t0 = time.time()
        with pytest.raises(Exception):
            await subject.run(counter.task)

        t1 = time.time()
        assert isclose(t1 - t0, 0.6, abs_tol=1e-01)
        assert counter.calls == 4
        assert counter.total == 0
