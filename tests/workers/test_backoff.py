import pytest

from mersal.workers import DefaultWorkerBackoffStrategy

__all__ = ("TestDefaultWorkerBackoffStrategy",)


pytestmark = pytest.mark.anyio


class TestDefaultWorkerBackoffStrategy:
    @pytest.fixture
    def slept(self, monkeypatch: pytest.MonkeyPatch) -> list[float]:
        recorded: list[float] = []

        async def fake_sleep(delay: float) -> None:
            recorded.append(delay)

        monkeypatch.setattr("mersal.workers.backoff.anyio.sleep", fake_sleep)
        return recorded

    async def test_escalates_through_delays_and_stays_at_the_last(self, slept: list[float]):
        strategy = DefaultWorkerBackoffStrategy(delays=[1.0, 2.0, 3.0])

        for _ in range(5):
            await strategy.wait_no_message()

        assert slept == [1.0, 2.0, 3.0, 3.0, 3.0]

    async def test_reset_restarts_the_progression(self, slept: list[float]):
        strategy = DefaultWorkerBackoffStrategy(delays=[1.0, 2.0])

        await strategy.wait_no_message()
        await strategy.wait_no_message()
        strategy.reset()
        await strategy.wait_no_message()

        assert slept == [1.0, 2.0, 1.0]

    async def test_consecutive_errors_escalate_through_error_delays(self, slept: list[float]):
        strategy = DefaultWorkerBackoffStrategy(error_delays=[1.0, 2.0, 5.0])

        for _ in range(4):
            await strategy.wait_error()

        assert slept == [1.0, 2.0, 5.0, 5.0]

    async def test_successful_empty_receive_resets_error_progression(self, slept: list[float]):
        strategy = DefaultWorkerBackoffStrategy(delays=[0.5], error_delays=[1.0, 2.0])

        await strategy.wait_error()
        await strategy.wait_error()
        await strategy.wait_no_message()
        await strategy.wait_error()

        assert slept == [1.0, 2.0, 0.5, 1.0]

    async def test_reset_restarts_the_error_progression(self, slept: list[float]):
        strategy = DefaultWorkerBackoffStrategy(error_delays=[1.0, 2.0])

        await strategy.wait_error()
        await strategy.wait_error()
        strategy.reset()
        await strategy.wait_error()

        assert slept == [1.0, 2.0, 1.0]

    async def test_rejects_empty_delays(self):
        with pytest.raises(ValueError, match="delays"):
            DefaultWorkerBackoffStrategy(delays=[])
        with pytest.raises(ValueError, match="error_delays"):
            DefaultWorkerBackoffStrategy(error_delays=[])
