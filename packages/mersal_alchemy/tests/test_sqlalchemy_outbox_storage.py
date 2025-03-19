from typing import cast

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from mersal.transport import DefaultTransactionContext
from mersal_alchemy import (
    SQLAlchemyOutboxStorage,
    SQLAlchemyOutboxStorageConfig,
)
from mersal_msgspec import MsgspecSerializer
from mersal_testing.test_doubles import (
    OutgoingMessageBuilder,
    TransportMessageBuilder,
)
from mersal_testing.testing_utils import is_docker_available

__all__ = ("TestSQLAlchemyOutboxStorage",)


pytestmark = [
    pytest.mark.anyio,
    pytest.mark.usefixtures("postgres_service"),
    pytest.mark.skipif(not is_docker_available(), reason="docker not available on this platform"),
]


class TestSQLAlchemyOutboxStorage:
    async def test_creates_table(self, db_engine: AsyncEngine):
        table_name = "outbox"
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemyOutboxStorageConfig(
            table_name=table_name,
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()

        async with db_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        assert table_name in tables

    async def test_with_created_table(self, db_engine: AsyncEngine):
        table_name = "outbox"
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemyOutboxStorageConfig(
            table_name=table_name,
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()
        await subject()

        async with db_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

        assert table_name in tables

    async def test_save_without_commit(self, db_engine: AsyncEngine):
        transport_message = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()
        outgoing_message = OutgoingMessageBuilder.build(transport_message=transport_message)
        outgoing_message2 = OutgoingMessageBuilder.build(transport_message=transport_message2)
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemyOutboxStorageConfig(
            table_name="outbox",
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
            commit_on_save=False,
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()
        transaction_context = DefaultTransactionContext()
        session = AsyncSession(db_engine)
        transaction_context.items["sqlalchemy-session"] = session
        await subject.save([outgoing_message, outgoing_message2], transaction_context)
        await session.close()

        session = AsyncSession(db_engine)
        async with session:
            saved_messages = (await session.scalars(select(subject.table))).all()
            assert len(saved_messages) == 0

    async def test_save_with_commit(self, db_engine: AsyncEngine):
        transport_message = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()
        outgoing_message = OutgoingMessageBuilder.build(transport_message=transport_message)
        outgoing_message2 = OutgoingMessageBuilder.build(transport_message=transport_message2)
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemyOutboxStorageConfig(
            table_name="outbox-special",
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
            commit_on_save=True,
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()
        transaction_context = DefaultTransactionContext()
        session = AsyncSession(db_engine, autoflush=False)
        transaction_context.items["sqlalchemy-session"] = session
        await subject.save([outgoing_message, outgoing_message2], transaction_context)
        async with session:
            saved_messages = (await session.scalars(select(subject.table))).all()
            assert len(saved_messages) == 2

    async def test_get_next_message_batch(self, db_engine: AsyncEngine):
        transport_message = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()
        outgoing_message = OutgoingMessageBuilder.build(transport_message=transport_message)
        outgoing_message2 = OutgoingMessageBuilder.build(transport_message=transport_message2)
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        config = SQLAlchemyOutboxStorageConfig(
            table_name="outbox",
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()
        transaction_context = DefaultTransactionContext()
        session = AsyncSession(db_engine)
        transaction_context.items["sqlalchemy-session"] = session
        await subject.save([outgoing_message, outgoing_message2], transaction_context)
        await session.commit()

        batch = await subject.get_next_message_batch()
        messages_in_batch = [
            x
            for x in list(batch)
            if str(x.headers.message_id) in [str(y.headers.message_id) for y in [transport_message, transport_message2]]
        ]
        assert len(messages_in_batch) == 2
        for m, om in zip(messages_in_batch, [outgoing_message, outgoing_message2], strict=False):
            assert m.body == om.transport_message.body
            assert m.destination_address == om.destination_address
            assert {k: str(v) for k, v in m.headers.items()} == {
                k: str(v) for k, v in om.transport_message.headers.items()
            }

    async def test_get_next_message_batch_completion(self, db_engine: AsyncEngine):
        transport_message = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()
        outgoing_message = OutgoingMessageBuilder.build(transport_message=transport_message)
        outgoing_message2 = OutgoingMessageBuilder.build(transport_message=transport_message2)
        async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

        config = SQLAlchemyOutboxStorageConfig(
            table_name="outbox",
            async_session_factory=async_session_factory,
            session_extractor=lambda tr: cast("AsyncSession", tr.items.get("sqlalchemy-session")),
        )

        subject = SQLAlchemyOutboxStorage(config)
        subject.headers_serializer = MsgspecSerializer(set())
        await subject()
        transaction_context = DefaultTransactionContext()
        session = AsyncSession(db_engine)
        transaction_context.items["sqlalchemy-session"] = session
        await subject.save([outgoing_message, outgoing_message2], transaction_context)
        await session.commit()

        batch = await subject.get_next_message_batch()
        await batch.complete()
        async with session:
            saved_messages = (await session.execute(select(subject.table))).all()
            for sm in saved_messages:
                assert sm.sent  # type: ignore
        batch = await subject.get_next_message_batch()
        assert not len(batch)
