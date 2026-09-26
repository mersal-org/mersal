import itertools
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import partial

from mersal.messages import MessageHeaders, TransportMessage
from mersal.timeouts import DueMessage, TimeoutManager

__all__ = ("InMemoryTimeoutManager",)


class InMemoryTimeoutManager(TimeoutManager):
    """Stores deferred messages in memory; they're lost when the process stops."""

    def __init__(self) -> None:
        self._messages: dict[int, tuple[datetime, TransportMessage]] = {}
        self._ids = itertools.count()

    def __len__(self) -> int:
        return len(self._messages)

    async def __call__(self) -> None: ...

    async def defer(self, due_time: datetime, message: TransportMessage) -> None:
        self._messages[next(self._ids)] = (due_time, TransportMessage(message.body, MessageHeaders(message.headers)))

    @asynccontextmanager
    async def get_due_messages(self) -> AsyncIterator[Sequence[DueMessage]]:
        now = datetime.now(UTC)
        due = sorted(
            ((due_time, _id, message) for _id, (due_time, message) in self._messages.items() if due_time <= now),
            key=lambda x: (x[0], x[1]),
        )
        yield [DueMessage(message, partial(self._complete, _id)) for _, _id, message in due]

    async def _complete(self, _id: int) -> None:
        self._messages.pop(_id, None)
