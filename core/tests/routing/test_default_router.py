import pytest

from mersal.routing.default import DefaultRouter
from mersal_testing.test_doubles import LogicalMessageBuilder

__all__ = (
    "Message1",
    "Message2",
    "TestDefaultRouter",
)


pytestmark = pytest.mark.anyio


class Message1:
    pass


class Message2:
    pass


class TestDefaultRouter:
    async def test_register_with_single_message_type_destination_address(self):
        subject = DefaultRouter()
        subject.register(Message1, "moon")
        subject.register(Message2, "sun")

        assert await subject.get_destination_address(LogicalMessageBuilder.build(_bytes=Message1())) == "moon"
        assert await subject.get_destination_address(LogicalMessageBuilder.build(_bytes=Message2())) == "sun"

    async def test_register_with_multiple_message_types_destination_address(self):
        subject = DefaultRouter()
        subject.register([Message1, Message2], "sun")
        assert await subject.get_destination_address(LogicalMessageBuilder.build(_bytes=Message1())) == "sun"
        assert await subject.get_destination_address(LogicalMessageBuilder.build(_bytes=Message2())) == "sun"
