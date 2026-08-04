from dataclasses import dataclass

from mersal.messages.message_headers import MessageHeaders
from mersal.messages.transport_message import TransportMessage

__all__ = ("OutboxMessage",)


@dataclass
class OutboxMessage:
    """Outbox message that is stored in the storage.

    It is a simple wrapper around a transport message and its destination in
    addition to a unique identity given to each outbox message.
    """

    destination_address: str
    "Destination address for the outbox message"
    headers: MessageHeaders
    "Message headers for the outbox message."
    body: bytes
    "Original body of the transport message."
    outbox_message_id: int | None = None  # typing: ignore
    """Outbox message identifier.

    The default being None is to make SQLAlchemy happy
    https://github.com/mersal-org/mersal/issues/17
    """

    def transport_message(self) -> TransportMessage:
        """Converts the message back to a TransportMessage."""
        return TransportMessage(self.body, self.headers)
