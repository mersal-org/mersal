from mersal.messages import LogicalMessage, TransportMessage
from mersal.serialization.serializers import MessageBodySerializer

__all__ = ("MessageSerializer",)


class MessageSerializer:
    def __init__(self, serializer: MessageBodySerializer) -> None:
        self._serializer = serializer

    async def serialize(self, logical_message: LogicalMessage) -> TransportMessage:
        body = self._serializer.serialize(logical_message.body)
        return TransportMessage(body, logical_message.headers)

    async def deserialize(self, transport_message: TransportMessage) -> LogicalMessage:
        body = self._serializer.deserialize(transport_message.body)
        return LogicalMessage(body, transport_message.headers)
