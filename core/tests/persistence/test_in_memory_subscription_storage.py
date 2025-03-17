import pytest

from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)

__all__ = ("TestInMemorySubcriptionStorage",)


pytestmark = pytest.mark.anyio


class TestInMemorySubcriptionStorage:
    async def test_register_unregister_and_get(self):
        subject = InMemorySubscriptionStorage.decentralized()
        topic1 = "T1"
        topic2 = "T2"
        topic1_subscribers = {"s1", "s2"}
        assert not await subject.get_subscriber_addresses(topic1)
        assert not await subject.get_subscriber_addresses(topic2)

        for s in topic1_subscribers:
            await subject.register_subscriber(topic1, s)

        assert await subject.get_subscriber_addresses(topic1) == topic1_subscribers
        assert not await subject.get_subscriber_addresses(topic2)

        await subject.unregister_subscriber(topic1, "s1")
        assert await subject.get_subscriber_addresses(topic1) == {"s2"}

        assert not subject.is_centralized
        subject2 = InMemorySubscriptionStorage.centralized(InMemorySubscriptionStore())
        assert subject2.is_centralized
