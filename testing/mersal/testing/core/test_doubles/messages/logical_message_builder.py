import json
import uuid
from dataclasses import dataclass
from typing import Any

from mersal.messages import BatchMessage, LogicalMessage
from mersal.messages.message_headers import MessageHeaders

__all__ = (
    "AnotherDummyMessage",
    "DummyMessage",
    "LogicalMessageBuilder",
)


@dataclass
class DummyMessage:
    data: str = "test"


@dataclass
class AnotherDummyMessage:
    data: str = "test"


class LogicalMessageBuilder:
    @staticmethod
    def build(use_dummy_message: bool = False, _bytes: Any | None = None) -> LogicalMessage:
        headers = MessageHeaders(message_id=str(uuid.uuid4()))
        if _bytes:
            return LogicalMessage(
                body=_bytes,
                headers=headers,
            )

        if use_dummy_message:
            _bytes = DummyMessage()
        else:
            data = {"a": 10}
            json_data = json.dumps(data)
            _bytes = bytes(json_data, "utf-8")
        return LogicalMessage(
            body=_bytes,
            headers=headers,
        )

    @staticmethod
    def build_batch_message(messages: list[Any]) -> LogicalMessage:
        return LogicalMessage(
            body=BatchMessage(messages),
            headers=MessageHeaders(message_id=str(uuid.uuid4())),
        )
