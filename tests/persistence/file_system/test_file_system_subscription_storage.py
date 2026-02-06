import pytest

from mersal.persistence.file_system import FileSystemSubscriptionStorage

__all__ = ("TestFileSystemSubscriptionStorage",)


pytestmark = pytest.mark.anyio


class TestFileSystemSubscriptionStorage:
    async def test_register_unregister_and_get(self, tmp_path):
        subject = FileSystemSubscriptionStorage.decentralized(tmp_path)
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
        subject2 = FileSystemSubscriptionStorage.centralized(tmp_path / "centralized")
        assert subject2.is_centralized

    async def test_centralized_shares_state(self, tmp_path):
        shared_dir = tmp_path / "shared"
        subject1 = FileSystemSubscriptionStorage.centralized(shared_dir)
        subject2 = FileSystemSubscriptionStorage.centralized(shared_dir)

        await subject1.register_subscriber("topic", "addr1")
        assert await subject2.get_subscriber_addresses("topic") == {"addr1"}

    async def test_data_persists_across_instances(self, tmp_path):
        subject1 = FileSystemSubscriptionStorage.decentralized(tmp_path)
        await subject1.register_subscriber("topic", "addr1")
        await subject1.register_subscriber("topic", "addr2")

        subject2 = FileSystemSubscriptionStorage.decentralized(tmp_path)
        assert await subject2.get_subscriber_addresses("topic") == {"addr1", "addr2"}
