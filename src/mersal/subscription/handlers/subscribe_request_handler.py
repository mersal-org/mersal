from mersal.messages.control import SubscribeRequest
from mersal.subscription.subscription_storage import SubscriptionStorage

__all__ = ("SubscribeRequestHandler",)


class SubscribeRequestHandler:
    def __init__(self, subscription_storage: SubscriptionStorage) -> None:
        self._subscription_storage = subscription_storage

    async def __call__(self, message: SubscribeRequest) -> None:
        await self._subscription_storage.register_subscriber(message.topic, message.subscriber_address)
