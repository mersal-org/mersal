import pytest

from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.testing.core.subscription.basic_subscription_storage_tests import (
    BasicSubscriptionStorageTest,
    SubscriptionStorageMaker,
)

__all__ = ("TestInMemorySubscriptionStorage",)


pytestmark = pytest.mark.anyio


class TestInMemorySubscriptionStorage(BasicSubscriptionStorageTest):
    @pytest.fixture
    def decentralized_storage_maker(self) -> SubscriptionStorageMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        def maker(**kwargs: object) -> InMemorySubscriptionStorage:
            return InMemorySubscriptionStorage.decentralized()

        return maker

    @pytest.fixture
    def centralized_storage_maker(self) -> SubscriptionStorageMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        store = InMemorySubscriptionStore()

        def maker(**kwargs: object) -> InMemorySubscriptionStorage:
            return InMemorySubscriptionStorage.centralized(store)

        return maker
