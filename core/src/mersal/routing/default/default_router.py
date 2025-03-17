from collections.abc import Iterable

from mersal.exceptions import MersalExceptionError
from mersal.messages import LogicalMessage
from mersal.routing.router import Router

__all__ = (
    "DefaultRouter",
    "NoRouteFoundError",
)


class NoRouteFoundError(MersalExceptionError):
    pass


class DefaultRouter(Router):
    def __init__(self) -> None:
        self._destination_addresses: dict[type, str] = {}

    def register(self, message_type: type | Iterable[type], destination_address: str) -> None:
        if not isinstance(message_type, Iterable):
            message_type = [message_type]

        for m in message_type:
            self._destination_addresses[m] = destination_address

    async def get_destination_address(self, message: LogicalMessage) -> str:
        if address := self._destination_addresses.get(type(message.body)):
            return address

        raise NoRouteFoundError()
