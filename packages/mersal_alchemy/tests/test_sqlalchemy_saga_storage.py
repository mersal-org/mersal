import uuid
from dataclasses import dataclass
from typing import Any, cast

import msgspec
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from mersal.exceptions.base_exceptions import (
    ConcurrencyExceptionError,
    MersalExceptionError,
)
from mersal.sagas import SagaData
from mersal.transport import DefaultTransactionContext
from mersal_alchemy import (
    SQLAlchemySagaStorageConfig,
)
from mersal_testing.testing_utils import is_docker_available

__all__ = (
    "MyExampleSagaData",
    "MyExampleSagaData2",
    "TestSQLAlchemySagaStorage",
)


pytestmark = [
    pytest.mark.anyio,
    pytest.mark.usefixtures("postgres_service"),
    pytest.mark.skipif(not is_docker_available(), reason="docker not available on this platform"),
]


@dataclass
class MyExampleSagaData:
    user_id: int | None = None
    name: str | None = None


@dataclass
class MyExampleSagaData2:
    user_id: int | None = None
    name: str | None = None


class TestSQLAlchemySagaStorage:
    @pytest.fixture
    def session_factory(self, db_engine_msgspec: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(db_engine_msgspec, expire_on_commit=False)

    @pytest.fixture
    def session(self, session_factory: async_sessionmaker[AsyncSession]):
        return session_factory()

    @pytest.fixture
    def table_name(self) -> str:
        return "sagas"

    @pytest.fixture
    def transaction_context(self, session: AsyncSession) -> DefaultTransactionContext:
        context = DefaultTransactionContext()
        context.items["sqlalchemy-session"] = session
        return context

    @pytest.fixture
    def config(self, session_factory: async_sessionmaker[AsyncSession], table_name: str) -> SQLAlchemySagaStorageConfig:
        return SQLAlchemySagaStorageConfig(
            table_name=table_name,
            async_session_factory=session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

    async def test_creates_table(
        self,
        db_engine: AsyncEngine,
        config: SQLAlchemySagaStorageConfig,
        table_name: str,
    ):
        subject = config.storage
        await subject()

        async with db_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        assert table_name in tables

    async def test_with_created_table(
        self,
        db_engine: AsyncEngine,
        config: SQLAlchemySagaStorageConfig,
        table_name: str,
    ):
        subject = config.storage
        await subject()
        await subject()

        async with db_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        assert table_name in tables

    async def test_insert(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=0, data=MyExampleSagaData())
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()

        data: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data

    async def test_update(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=0, data=MyExampleSagaData())
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()

        data1: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data1

        data1.data["name"] = "Simpson"
        await subject.update(data1, [], transaction_context)
        await session.commit()
        await session.close()

        data2: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data2
        assert data2.data["name"] == "Simpson"

    async def test_delete(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session_factory: async_sessionmaker[AsyncSession],
        session: AsyncSession,
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=0, data=MyExampleSagaData())
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()

        async with session_factory() as session:
            data1: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
            assert data1

        session = session_factory()
        transaction_context.items["sqlalchemy-session"] = session
        await subject.delete(data1, transaction_context)
        await session.commit()
        await session.close()
        data2: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)

        assert not data2

    async def test_find(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(
            id=uuid.uuid4(),
            revision=0,
            data=MyExampleSagaData(user_id=10, name="Smith"),
        )
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()

        data = await subject.find(MyExampleSagaData, "user_id", saga_data.data.user_id)
        assert data
        assert data.id == saga_data.id

    async def test_find_with_custom_decoder(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        def decode(obj: Any, typ: Any):
            return msgspec.convert(obj, type=typ)

        config.from_json = decode
        subject = config.storage
        await subject()
        saga_data = SagaData(
            id=uuid.uuid4(),
            revision=0,
            data=MyExampleSagaData(user_id=20, name="Smith"),
        )
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()

        data = await subject.find(MyExampleSagaData, "user_id", saga_data.data.user_id)
        assert data
        assert data.id == saga_data.id
        assert type(data.data) is MyExampleSagaData

    async def test_insert_and_update_with_custom_encoder(
        self,
        db_engine: AsyncEngine,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemySagaStorageConfig(
            async_session_factory=session_factory,
            table_name="sagas",
            to_json_compatible=lambda x: msgspec.to_builtins(x),
            from_json=lambda x, y: msgspec.convert(x, type=y),
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=0, data=MyExampleSagaData())
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()
        data1: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data1
        data1.data.name = "Simpson"
        session = session_factory()
        transaction_context.items["sqlalchemy-session"] = session
        await subject.update(data1, [], transaction_context)
        await session.commit()
        await session.close()

        data2: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data2
        assert data2.data.name == "Simpson"

    async def test_insert_with_non_zero_revision(
        self,
        config: SQLAlchemySagaStorageConfig,
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=1, data=MyExampleSagaData())
        transaction_context = DefaultTransactionContext()
        with pytest.raises(MersalExceptionError):
            await subject.insert(saga_data, [], transaction_context)

    async def test_find_with_two_saga_types_sharing_properties(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
    ):
        subject = config.storage
        await subject()
        saga_data1 = SagaData(
            id=uuid.uuid4(),
            revision=0,
            data=MyExampleSagaData(user_id=50, name="Smith"),
        )
        saga_data2 = SagaData(
            id=uuid.uuid4(),
            revision=0,
            data=MyExampleSagaData2(user_id=50, name="Smith"),
        )
        await subject.insert(saga_data2, [], transaction_context)
        await subject.insert(saga_data1, [], transaction_context)
        await session.commit()
        await session.close()

        data = await subject.find(MyExampleSagaData, "user_id", saga_data1.data.user_id)
        assert data
        assert data.id == saga_data1.id

    async def test_update_with_concurrency_issue(
        self,
        config: SQLAlchemySagaStorageConfig,
        transaction_context: DefaultTransactionContext,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        subject = config.storage
        await subject()
        saga_data = SagaData(id=uuid.uuid4(), revision=0, data=MyExampleSagaData())
        await subject.insert(saga_data, [], transaction_context)
        await session.commit()
        await session.close()
        data: SagaData | None = await subject.find_using_id(MyExampleSagaData, saga_data.id)
        assert data

        data.data["name"] = "Simpson"
        session = session_factory()
        transaction_context.items["sqlalchemy-session"] = session
        await subject.update(data, [], transaction_context)
        await session.commit()
        with pytest.raises(ConcurrencyExceptionError):
            await subject.update(data, [], transaction_context)
        await session.close()
