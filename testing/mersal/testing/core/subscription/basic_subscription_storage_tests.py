from typing import Any, Protocol

import pytest

from mersal.subscription import SubscriptionStorage

__all__ = (
    "BasicSubscriptionStorageTest",
    "SubscriptionStorageMaker",
)


pytestmark = pytest.mark.anyio


class SubscriptionStorageMaker(Protocol):
    def __call__(self, **kwargs: Any) -> SubscriptionStorage: ...


class BasicSubscriptionStorageTest:
    supports_decentralized: bool = True
    supports_centralized: bool = True

    @pytest.fixture
    def decentralized_storage_maker(self) -> SubscriptionStorageMaker:
        def maker(**kwargs: Any) -> SubscriptionStorage:
            raise NotImplementedError()

        return maker

    @pytest.fixture
    def centralized_storage_maker(self) -> SubscriptionStorageMaker:
        """Each call must return an instance backed by the *same* shared store, so that
        registrations made through one instance are visible through another - mirroring how
        multiple apps point at one shared, centralized backend.
        """

        def maker(**kwargs: Any) -> SubscriptionStorage:
            raise NotImplementedError()

        return maker

    async def test_decentralized_register_unregister_and_get(
        self, decentralized_storage_maker: SubscriptionStorageMaker
    ) -> None:
        if not self.supports_decentralized:
            pytest.skip("This storage does not support decentralized mode.")

        subject = decentralized_storage_maker()
        assert not subject.is_centralized

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

    async def test_centralized_storage_is_shared_across_instances(
        self, centralized_storage_maker: SubscriptionStorageMaker
    ) -> None:
        if not self.supports_centralized:
            pytest.skip("This storage does not support centralized mode.")

        subject1 = centralized_storage_maker()
        subject2 = centralized_storage_maker()
        assert subject1.is_centralized
        assert subject2.is_centralized

        await subject1.register_subscriber("topic", "addr1")
        assert await subject2.get_subscriber_addresses("topic") == {"addr1"}

        await subject2.unregister_subscriber("topic", "addr1")
        assert await subject1.get_subscriber_addresses("topic") == set()
