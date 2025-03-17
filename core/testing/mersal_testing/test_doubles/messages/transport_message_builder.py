import json
import uuid

from mersal.messages.message_headers import MessageHeaders
from mersal.messages.transport_message import TransportMessage

__all__ = ("TransportMessageBuilder",)


class TransportMessageBuilder:
    @staticmethod
    def build() -> TransportMessage:
        data = {"a": 10}
        json_data = json.dumps(data)
        _bytes = bytes(json_data, "utf-8")
        return TransportMessage(
            body=_bytes,
            headers=MessageHeaders(message_id=uuid.uuid4()),
        )
