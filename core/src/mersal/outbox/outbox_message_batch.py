from collections.abc import Iterable, Iterator, Sequence

from mersal.outbox.outbox_message import OutboxMessage
from mersal.types import AsyncAnyCallable

__all__ = ("OutboxMessage", "OutboxMessageBatch")


class OutboxMessageBatch(Sequence[OutboxMessage]):
    def __init__(
        self,
        messages: Iterable[OutboxMessage],
        complete_action: AsyncAnyCallable,
        close_action: AsyncAnyCallable,
    ) -> None:
        self._messages = list(messages)
        self._complete_action = complete_action
        self._close_action = close_action

    async def complete(self) -> None:
        await self._complete_action()

    async def close(self) -> None:
        await self._close_action()

    def __len__(self) -> int:
        return len(self._messages)

    def __iter__(self) -> Iterator[OutboxMessage]:
        return iter(self._messages)

    def __getitem__(self, index: int) -> OutboxMessage:  # type: ignore[override]
        return self._messages[index]
