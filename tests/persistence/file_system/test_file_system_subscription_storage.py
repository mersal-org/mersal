import pytest

from mersal.persistence.file_system import FileSystemSubscriptionStorage
from mersal_testing.subscription.basic_subscription_storage_tests import (
    BasicSubscriptionStorageTest,
    SubscriptionStorageMaker,
)

__all__ = ("TestFileSystemSubscriptionStorage",)


pytestmark = pytest.mark.anyio


class TestFileSystemSubscriptionStorage(BasicSubscriptionStorageTest):
    @pytest.fixture
    def decentralized_storage_maker(self, tmp_path) -> SubscriptionStorageMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        def maker(**kwargs: object) -> FileSystemSubscriptionStorage:
            return FileSystemSubscriptionStorage.decentralized(tmp_path)

        return maker

    @pytest.fixture
    def centralized_storage_maker(self, tmp_path) -> SubscriptionStorageMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        shared_dir = tmp_path / "shared"

        def maker(**kwargs: object) -> FileSystemSubscriptionStorage:
            return FileSystemSubscriptionStorage.centralized(shared_dir)

        return maker

    async def test_data_persists_across_instances(self, tmp_path):
        subject1 = FileSystemSubscriptionStorage.decentralized(tmp_path)
        await subject1.register_subscriber("topic", "addr1")
        await subject1.register_subscriber("topic", "addr2")

        subject2 = FileSystemSubscriptionStorage.decentralized(tmp_path)
        assert await subject2.get_subscriber_addresses("topic") == {"addr1", "addr2"}
