from typing import Protocol

__all__ = ("SubscriptionStorage",)


class SubscriptionStorage(Protocol):
    async def get_subscriber_addresses(self, topic: str) -> set[str]: ...

    async def register_subscriber(self, topic: str, subscriber_address: str) -> None: ...

    async def unregister_subscriber(self, topic: str, subscriber_address: str) -> None: ...

    @property
    def is_centralized(self) -> bool: ...
