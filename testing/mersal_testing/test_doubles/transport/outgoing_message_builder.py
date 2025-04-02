from mersal.messages.transport_message import TransportMessage
from mersal.transport import OutgoingMessage

__all__ = ("OutgoingMessageBuilder",)


class OutgoingMessageBuilder:
    @staticmethod
    def build(transport_message: TransportMessage, destination_address: str = "moon") -> OutgoingMessage:
        return OutgoingMessage(destination_address=destination_address, transport_message=transport_message)
