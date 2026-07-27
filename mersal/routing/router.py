from typing import Protocol

from mersal.messages import LogicalMessage

__all__ = ("Router",)


class Router(Protocol):
    async def get_destination_address(self, message: LogicalMessage) -> str: ...

    async def get_owner_address(self, topic: str) -> str:
        """Get the address of the app that owns (publishes) the given topic.

        Used when subscribing/unsubscribing against decentralized subscription storage,
        where the request has to be routed to the topic's publisher rather than written
        to a shared store directly.
        """
        ...
