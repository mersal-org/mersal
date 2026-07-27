from dataclasses import dataclass

__all__ = ("UnsubscribeRequest",)


@dataclass
class UnsubscribeRequest:
    """Control message sent to a topic's owner to end a subscription.

    Used when the subscription storage is decentralized, i.e. there is no shared
    store the subscriber can unregister itself from directly.
    """

    topic: str
    subscriber_address: str
