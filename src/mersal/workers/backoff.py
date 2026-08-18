from collections.abc import Sequence
from typing import Protocol

import anyio

__all__ = (
    "DefaultWorkerBackoffStrategy",
    "WorkerBackoffStrategy",
)


class WorkerBackoffStrategy(Protocol):
    """Controls how a worker waits between receive attempts.

    Transports return None within a bounded time when no message is
    available; idle waiting is the worker's job, driven by this strategy.
    This keeps an idle worker from spinning on an empty queue, keeps a
    persistently failing transport from spinning on errors, and keeps the
    worker's receive-loop heartbeat meaningful as a liveness signal.
    """

    async def wait_no_message(self) -> None:
        """Wait after a receive attempt that returned no message."""
        ...

    async def wait_error(self) -> None:
        """Wait after a receive attempt that raised, to avoid a hot error loop."""
        ...

    def reset(self) -> None:
        """Reset the backoff after a message was received."""
        ...


class DefaultWorkerBackoffStrategy:
    """Backs off progressively while the queue stays empty or receives fail.

    Each consecutive empty receive moves one step further into ``delays``,
    staying at the final delay once reached; receiving a message resets the
    progression. The default progression caps at 0.25s, bounding the pickup
    latency an idle worker adds to a freshly arrived message.

    Consecutive receive errors escalate separately through ``error_delays``
    (e.g. expired credentials or a deleted queue won't spin the loop); any
    successful receive attempt, even an empty one, resets that progression.
    """

    def __init__(
        self,
        delays: Sequence[float] | None = None,
        error_delays: Sequence[float] | None = None,
    ) -> None:
        self._delays = list(delays) if delays is not None else [0.02, 0.05, 0.1, 0.25]
        if not self._delays:
            raise ValueError("delays must not be empty")
        self._error_delays = list(error_delays) if error_delays is not None else [0.5, 1.0, 2.0, 5.0]
        if not self._error_delays:
            raise ValueError("error_delays must not be empty")
        self._consecutive_empty = 0
        self._consecutive_errors = 0

    async def wait_no_message(self) -> None:
        self._consecutive_errors = 0
        index = min(self._consecutive_empty, len(self._delays) - 1)
        self._consecutive_empty += 1
        await anyio.sleep(self._delays[index])

    async def wait_error(self) -> None:
        index = min(self._consecutive_errors, len(self._error_delays) - 1)
        self._consecutive_errors += 1
        await anyio.sleep(self._error_delays[index])

    def reset(self) -> None:
        self._consecutive_empty = 0
        self._consecutive_errors = 0
