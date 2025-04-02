from collections.abc import Callable, MutableSequence, Sequence
from random import randint
from typing import cast

from mersal.outbox import OutboxStorage
from mersal.outbox.outbox_message import OutboxMessage
from mersal.outbox.outbox_message_batch import OutboxMessageBatch
from mersal.serialization.identity_serializer import IdentitySerializer
from mersal.transport import OutgoingMessage, TransactionContext

__all__ = ("OutboxStorageTestDouble",)


class OutboxStorageTestDouble(OutboxStorage):
    def __init__(self) -> None:
        self.saved_outgoing_messages: MutableSequence[tuple[MutableSequence[OutgoingMessage], TransactionContext]] = []
        self.headers_serializer = IdentitySerializer()
        self._complete_action: Callable[[], None] = lambda: None
        self._close_action: Callable[[], None] = lambda: None

    async def __call__(self) -> None: ...

    async def save(
        self,
        outgoing_messages: Sequence[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        # Convert Sequence to a list since Sequence doesn't guarantee a copy method
        self.saved_outgoing_messages.append(
            (
                cast("MutableSequence[OutgoingMessage]", list(outgoing_messages)),
                transaction_context,
            )
        )

    async def get_next_message_batch(self) -> OutboxMessageBatch:
        outbox_messages: list[OutboxMessage] = []
        while self.saved_outgoing_messages:
            item = self.saved_outgoing_messages.pop(0)
            while messages := item[0]:
                message = messages.pop(0)
                outbox_messages.append(
                    OutboxMessage(
                        outbox_message_id=randint(1, 100000),  # noqa: S311
                        destination_address=message.destination_address,
                        headers=message.transport_message.headers,
                        body=message.transport_message.body,
                    )
                )

        async def complete_action() -> None:
            self._complete_action()

        async def close_action() -> None:
            self._close_action()

        return OutboxMessageBatch(
            messages=outbox_messages,
            complete_action=complete_action,
            close_action=close_action,
        )
