import uuid
from dataclasses import dataclass

import pytest

from mersal.exceptions.base_exceptions import ConcurrencyExceptionError
from mersal.persistence.file_system import FileSystemSagaStorage
from mersal.sagas.saga_data import SagaData
from mersal.transport import DefaultTransactionContext

__all__ = ("TestFileSystemSagaStorage",)


pytestmark = pytest.mark.anyio


@dataclass
class OrderSagaData:
    order_id: str
    status: str = "pending"


class TestFileSystemSagaStorage:
    @pytest.fixture
    async def storage(self, tmp_path):
        storage = FileSystemSagaStorage(tmp_path)
        await storage()
        return storage

    async def test_call_clears_store(self, tmp_path):
        storage = FileSystemSagaStorage(tmp_path)
        await storage()

        async with DefaultTransactionContext() as ctx:
            saga = SagaData(id=uuid.uuid4(), revision=0, data=OrderSagaData(order_id="123"))
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        await storage()

        async with DefaultTransactionContext() as ctx:
            result = await storage.find(OrderSagaData, "order_id", "123")
            assert result is None
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

    async def test_insert_and_find_by_id(self, storage):
        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="123"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        result = await storage.find_using_id(OrderSagaData, saga_id)
        assert result is not None
        assert result.id == saga_id
        assert result.data.order_id == "123"

    async def test_insert_and_find_by_property(self, storage):
        saga = SagaData(id=uuid.uuid4(), revision=0, data=OrderSagaData(order_id="456"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        result = await storage.find(OrderSagaData, "order_id", "456")
        assert result is not None
        assert result.data.order_id == "456"

    async def test_find_returns_none_for_missing(self, storage):
        result = await storage.find_using_id(OrderSagaData, uuid.uuid4())
        assert result is None

        result = await storage.find(OrderSagaData, "order_id", "nonexistent")
        assert result is None

    async def test_insert_duplicate_raises(self, storage):
        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="123"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        with pytest.raises(Exception, match="already exist"):
            async with DefaultTransactionContext() as ctx:
                await storage.insert(saga, [], ctx)

    async def test_insert_with_nonzero_revision_raises(self, storage):
        saga = SagaData(id=uuid.uuid4(), revision=1, data=OrderSagaData(order_id="123"))

        with pytest.raises(Exception, match="revision=0"):
            async with DefaultTransactionContext() as ctx:
                await storage.insert(saga, [], ctx)

    async def test_update_increments_revision(self, storage):
        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="123"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        found = await storage.find_using_id(OrderSagaData, saga_id)
        assert found is not None
        found.data.status = "completed"

        async with DefaultTransactionContext() as ctx:
            await storage.update(found, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        assert found.revision == 1

        updated = await storage.find_using_id(OrderSagaData, saga_id)
        assert updated is not None
        assert updated.revision == 1
        assert updated.data.status == "completed"

    async def test_update_with_wrong_revision_raises(self, storage):
        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="123"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        stale = SagaData(id=saga_id, revision=5, data=OrderSagaData(order_id="123"))

        with pytest.raises(ConcurrencyExceptionError):
            async with DefaultTransactionContext() as ctx:
                await storage.update(stale, [], ctx)

    async def test_delete(self, storage):
        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="123"))

        async with DefaultTransactionContext() as ctx:
            await storage.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        async with DefaultTransactionContext() as ctx:
            await storage.delete(saga, ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        result = await storage.find_using_id(OrderSagaData, saga_id)
        assert result is None

    async def test_data_persists_across_instances(self, tmp_path):
        storage1 = FileSystemSagaStorage(tmp_path)
        await storage1()

        saga_id = uuid.uuid4()
        saga = SagaData(id=saga_id, revision=0, data=OrderSagaData(order_id="789"))

        async with DefaultTransactionContext() as ctx:
            await storage1.insert(saga, [], ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        storage2 = FileSystemSagaStorage(tmp_path)
        result = await storage2.find_using_id(OrderSagaData, saga_id)
        assert result is not None
        assert result.data.order_id == "789"
