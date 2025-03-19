import uuid
from dataclasses import dataclass

import pytest

from mersal_msgspec import MsgspecSerializer

__all__ = (
    "Message1",
    "test_msgspec_dict_serialization",
    "test_msgspec_object_serialization",
)


pytestmark = pytest.mark.anyio


@dataclass
class Message1:
    name: str


async def test_msgspec_object_serialization():
    subject = MsgspecSerializer(
        object_types={
            Message1,
        }
    )

    message = Message1(name="A")

    encoded_message = subject.serialize(message)

    decoded_message = subject.deserialize(encoded_message)

    assert decoded_message == message


@pytest.mark.skip
async def test_msgspec_dict_serialization():
    subject = MsgspecSerializer(object_types=set())

    data = {"a": 10, "b": uuid.uuid4()}
    encoded_message = subject.serialize(data)

    decoded_data = subject.deserialize(encoded_message)

    assert decoded_data == data
