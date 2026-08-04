from mersal.messages.control import UnsubscribeRequest
from mersal.subscription.subscription_storage import SubscriptionStorage

__all__ = ("UnsubscribeRequestHandler",)


class UnsubscribeRequestHandler:
    def __init__(self, subscription_storage: SubscriptionStorage) -> None:
        self._subscription_storage = subscription_storage

    async def __call__(self, message: UnsubscribeRequest) -> None:
        await self._subscription_storage.unregister_subscriber(message.topic, message.subscriber_address)
