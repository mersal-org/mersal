from mersal.messages import LogicalMessage, TransportMessage
from mersal.serialization import MessageSerializer

__all__ = ("SerializerTestDouble",)


class SerializerTestDouble(MessageSerializer):
    def __init__(self) -> None:
        # Use union types with None for test doubles
        self.serialize_stub: TransportMessage | None = None
        self.deserialize_stub: LogicalMessage | None = None

    async def serialize(self, logical_message: LogicalMessage) -> TransportMessage:
        # Since this is a test double, we know serialize_stub will be set before calling
        assert self.serialize_stub is not None, "serialize_stub must be set before use"
        return self.serialize_stub

    async def deserialize(self, transport_message: TransportMessage) -> LogicalMessage:
        # Since this is a test double, we know deserialize_stub will be set before calling
        assert self.deserialize_stub is not None, "deserialize_stub must be set before use"
        return self.deserialize_stub
