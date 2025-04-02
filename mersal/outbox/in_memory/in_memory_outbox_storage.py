from collections.abc import Sequence
from random import randint

from mersal.outbox.outbox_message import OutboxMessage
from mersal.outbox.outbox_message_batch import OutboxMessageBatch
from mersal.outbox.outbox_storage import OutboxStorage
from mersal.transport import OutgoingMessage, TransactionContext

__all__ = ("InMemoryOutboxStorage",)


class InMemoryOutboxStorage(OutboxStorage):
    def __init__(self) -> None:
        self._store: dict[int, OutboxMessage] = {}
        self._forwarded: set[int] = set()

    async def save(
        self,
        outgoing_messages: Sequence[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        for message in outgoing_messages:
            _id = randint(1, 1000000)  # noqa: S311
            self._store[_id] = OutboxMessage(
                outbox_message_id=_id,
                destination_address=message.destination_address,
                headers=message.transport_message.headers,
                body=message.transport_message.body,
            )

    async def get_next_message_batch(self) -> OutboxMessageBatch:
        messages_in_batch = []
        unsent_messages_keys = [x for x in self._store if x not in self._forwarded]
        messages_in_batch = [self._store[x] for x in unsent_messages_keys]

        async def completion() -> None:
            self._forwarded.union(set(unsent_messages_keys))

        async def close() -> None:
            pass

        return OutboxMessageBatch(messages_in_batch, completion, close)

    async def __call__(self) -> None: ...
