from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.orm import registry

from mersal.messages.message_headers import MessageHeaders
from mersal.outbox import OutboxMessage, OutboxMessageBatch, OutboxStorage
from mersal_alchemy.orm import create_outbox_table_and_map

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from mersal.serialization import MessageHeadersSerializer
    from mersal.transport import OutgoingMessage, TransactionContext

__all__ = (
    "SQLAlchemyOutboxStorage",
    "SQLAlchemyOutboxStorageConfig",
)


@dataclass
class SQLAlchemyOutboxStorageConfig:
    """Configuration for SQLAlchemyOutboxStorage."""

    async_session_factory: async_sessionmaker[AsyncSession]
    """Session factory used to create a session responsible for the outbox table and fetch outbox messages.

    This is not used for creating the session responsible for saving the messages.
    """
    table_name: str
    "Outbox table name."
    session_extractor: Callable[[TransactionContext], AsyncSession]
    "A callback used to obtain the SQLAlchemy session from the current TransactionContext."
    commit_on_save: bool = True
    """Commit session at the end of the save method.

    This defaults to True but should be set to False if something else is taking care
    of committing the session. Check the :doc:`documentation </usage/outbox>` for examples.
    """
    close_session_on_save: bool = True
    """Close session at the end of the save method.

    This only applies if the session is also being committed.
    """

    @property
    def storage(self) -> SQLAlchemyOutboxStorage:
        return SQLAlchemyOutboxStorage(self)


class SQLAlchemyOutboxStorage(OutboxStorage):
    def __init__(
        self,
        config: SQLAlchemyOutboxStorageConfig,
    ) -> None:
        self._session_maker = config.async_session_factory
        self._table_name = config.table_name
        self._session_extractor = config.session_extractor
        self._commit_on_save = config.commit_on_save
        self._close_session_on_save = config.close_session_on_save
        self.headers_serializer: MessageHeadersSerializer

    async def save(
        self,
        outgoing_messages: Sequence[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        session = self._session_extractor(transaction_context)
        await session.execute(
            insert(self.table),
            [
                {
                    "destination_address": om.destination_address,
                    "headers": self.headers_serializer.serialize(om.transport_message.headers),
                    "body": om.transport_message.body,
                }
                for om in outgoing_messages
            ],
        )
        if self._commit_on_save:
            await session.commit()
            if self._close_session_on_save:
                await session.close()

    async def get_next_message_batch(self) -> OutboxMessageBatch:
        session = self._session_maker()
        async with session:
            stmt = select(self.table).where(self.table.c.sent == False)  # noqa: E712
            data = (await session.execute(stmt)).all()
            result = [
                OutboxMessage(
                    outbox_message_id=datum.outbox_message_id,
                    destination_address=datum.destination_address,
                    headers=MessageHeaders(self.headers_serializer.deserialize(datum.headers)),
                    body=datum.body,
                )
                for datum in data
            ]

            async def completion() -> None:
                await self._update_messages_sent_status(result, session)

            async def close() -> None:
                pass

            return OutboxMessageBatch(result, completion, close)

    async def __call__(self) -> None:
        self.table = create_outbox_table_and_map(self._table_name, registry())
        async with self._session_maker() as session:
            await session.run_sync(lambda s: self.table.create(s.get_bind(), checkfirst=True))

    async def _update_messages_sent_status(
        self, outbox_messages: Sequence[OutboxMessage], session: AsyncSession
    ) -> None:
        await session.execute(
            update(self.table)
            .where(self.table.c.outbox_message_id.in_([x.outbox_message_id for x in outbox_messages]))
            .values(sent=True),
        )

        await session.commit()
