from typing import Protocol

__all__ = ("SubscriptionStorage",)


class SubscriptionStorage(Protocol):
    """A protocol that defines the storage required to store topics subscriptions."""

    async def get_subscriber_addresses(self, topic: str) -> set[str]:
        """Get addresses subscribed for the given topic.

        Args:
            topic: topic name to get the addresses for.

        Returns:
            A set of addresses subscribed to this topic.
        """
        ...

    async def register_subscriber(self, topic: str, subscriber_address: str) -> None:
        """Register the given address for the given topic."""
        ...

    async def unregister_subscriber(self, topic: str, subscriber_address: str) -> None:
        """Unregister the given address for the given topic."""
        ...

    @property
    def is_centralized(self) -> bool:
        """Whether this storage is centralized.

        Centralized storage means topic subscriptions are stored in one place and
        registration/unregistration can be done by directly calling `register_subscriber`
        and `unregister_subscriber`, respectively.

        Non centralized means each topic handles its own storage and registration/unregistration
        is performed by sending a message to the topic owner (async).
        """
        ...
