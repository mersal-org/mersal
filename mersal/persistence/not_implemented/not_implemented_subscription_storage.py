from mersal.subscription import SubscriptionStorage

__all__ = ("NotImplementedSubscriptionStorage",)


class NotImplementedSubscriptionStorage(SubscriptionStorage):
    async def register_subscriber(self, topic: str, subscriber_address: str) -> None:
        raise self._exception()

    async def get_subscriber_addresses(self, topic: str) -> set[str]:
        raise self._exception()

    @property
    def is_centralized(self) -> bool:
        raise self._exception()

    async def unregister_subscriber(self, topic: str, subscriber_address: str) -> None:
        raise self._exception()

    def _exception(self) -> NotImplementedError:
        return NotImplementedError("Subscription storage not set. Cannot use pub/sub.")
