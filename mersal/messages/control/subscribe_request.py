from dataclasses import dataclass

__all__ = ("SubscribeRequest",)


@dataclass
class SubscribeRequest:
    """Control message sent to a topic's owner to establish a subscription.

    Used when the subscription storage is decentralized, i.e. there is no shared
    store the subscriber can register itself in directly.
    """

    topic: str
    subscriber_address: str
