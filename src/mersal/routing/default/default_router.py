from collections.abc import Iterable

from mersal.exceptions import MersalExceptionError
from mersal.messages import LogicalMessage
from mersal.routing.router import Router
from mersal.topic import DefaultTopicNameConvention, TopicNameConvention

__all__ = (
    "DefaultRouter",
    "NoRouteFoundError",
)


class NoRouteFoundError(MersalExceptionError):
    pass


class DefaultRouter(Router):
    def __init__(self, topic_name_convention: TopicNameConvention | None = None) -> None:
        self._topic_name_convention = topic_name_convention or DefaultTopicNameConvention()
        self._destination_addresses: dict[type, str] = {}
        self._owner_addresses: dict[str, str] = {}

    def register(self, message_type: type | Iterable[type], destination_address: str) -> None:
        message_types = [message_type] if isinstance(message_type, type) else message_type

        for m in message_types:
            self._destination_addresses[m] = destination_address
            self._owner_addresses[self._topic_name_convention.get_topic_name(m)] = destination_address

    async def get_destination_address(self, message: LogicalMessage) -> str:
        if address := self._destination_addresses.get(type(message.body)):
            return address

        raise NoRouteFoundError()

    async def get_owner_address(self, topic: str) -> str:
        if address := self._owner_addresses.get(topic):
            return address

        raise NoRouteFoundError()
