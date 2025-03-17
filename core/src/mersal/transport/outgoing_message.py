from dataclasses import dataclass

from mersal.messages import TransportMessage

__all__ = ("OutgoingMessage",)


@dataclass
class OutgoingMessage:
    """A convenience class wrapping a transport message and its destination."""

    destination_address: str
    "Destination address for the outgoing message."
    transport_message: TransportMessage
    "Message to be sent to the transport."
