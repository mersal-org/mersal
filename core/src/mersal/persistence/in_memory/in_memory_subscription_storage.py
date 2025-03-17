from __future__ import annotations

from collections import defaultdict
from collections.abc import MutableSet
from typing import Any

from typing_extensions import Self

from mersal.subscription import SubscriptionStorage

__all__ = (
    "InMemorySubscriptionStorage",
    "InMemorySubscriptionStore",
)


class InMemorySubscriptionStore(defaultdict[str, MutableSet[str]]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.default_factory = set


class InMemorySubscriptionStorage(SubscriptionStorage):
    __slots__ = ["_is_centralized", "_subscribers"]

    def __init__(self) -> None:
        self._is_centralized: bool = None  # type: ignore[assignment]
        self._subscribers: InMemorySubscriptionStore = None  # type: ignore[assignment]
        raise NotImplementedError()

    @classmethod
    def centralized(cls, store: InMemorySubscriptionStore) -> Self:
        obj = cls.__new__(cls)
        obj._init(store)
        return obj

    @classmethod
    def decentralized(cls) -> Self:
        obj = cls.__new__(cls)
        obj._init(None)
        return obj

    def _init(self, store: InMemorySubscriptionStore | None) -> None:
        self._is_centralized = store is not None
        self._subscribers = store if store is not None else InMemorySubscriptionStore()

    async def register_subscriber(self, topic: str, subscriber_address: str) -> None:
        self._subscribers[topic].add(subscriber_address)

    async def get_subscriber_addresses(self, topic: str) -> set[str]:
        return set(self._subscribers[topic])

    @property
    def is_centralized(self) -> bool:
        return self._is_centralized

    async def unregister_subscriber(self, topic: str, subscriber_address: str) -> None:
        self._subscribers[topic].remove(subscriber_address)
