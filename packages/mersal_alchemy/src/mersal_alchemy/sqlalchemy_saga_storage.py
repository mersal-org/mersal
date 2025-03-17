from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import registry
from sqlalchemy.sql import insert

from mersal.exceptions.base_exceptions import (
    ConcurrencyExceptionError,
    MersalExceptionError,
)
from mersal.sagas import CorrelationProperty, SagaData, SagaStorage
from mersal_alchemy.orm import create_sagas_table

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.schema import Table

    from mersal.transport import TransactionContext

__all__ = (
    "SQLAlchemySagaStorage",
    "SQLAlchemySagaStorageConfig",
)


@dataclass
class SQLAlchemySagaStorageConfig:
    async_session_factory: async_sessionmaker[AsyncSession]
    table_name: str
    session_extractor: Callable[[TransactionContext], AsyncSession]
    to_json_compatible: Callable[[Any], Any] | None = None
    from_json: Callable[[Any, type], Any] | None = None

    @property
    def storage(self) -> SQLAlchemySagaStorage:
        return SQLAlchemySagaStorage(self)


class SQLAlchemySagaStorage(SagaStorage):
    def __init__(
        self,
        config: SQLAlchemySagaStorageConfig,
    ) -> None:
        self._session_maker = config.async_session_factory
        self._table_name = config.table_name
        self._session_extractor = config.session_extractor
        self._to_json_compatible = config.to_json_compatible
        self._from_json = config.from_json
        self._table: Table

    async def __call__(self) -> None:
        self._table = create_sagas_table(self._table_name, registry())
        async with self._session_maker() as session:
            await session.run_sync(lambda s: self._table.create(s.get_bind(), checkfirst=True))

    async def find_using_id(self, saga_data_type: type, message_id: uuid.UUID) -> SagaData | None:
        stmt = select(self._table).where(self._table.c.id == message_id)
        async with self._session_maker() as session:
            result = (await session.execute(stmt)).one_or_none()
            if result:
                saga_data = self._convert_result(result)
                if self._from_json and result:
                    saga_data.data = self._from_json(result.data, saga_data_type)
            else:
                return None

            return saga_data

    async def find(self, saga_data_type: type, property_name: str, property_value: Any) -> SagaData | None:
        stmt = (
            select(self._table)
            .where(self._table.c.saga_type == saga_data_type.__name__)
            .where(self._table.c.data[property_name].as_string() == str(property_value))
        )
        async with self._session_maker() as session:
            result = (await session.execute(stmt)).one_or_none()
            if result:
                saga_data = self._convert_result(result)
                if self._from_json and result:
                    saga_data.data = self._from_json(result.data, saga_data_type)
            else:
                return None

            return saga_data

    async def insert(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        if saga_data.revision != 0:
            raise MersalExceptionError(saga_data, "Inserted SagaData revision is not 0")
        if self._session_extractor is not None:
            session = self._session_extractor(transaction_context)
            await self._execute_insert(saga_data, session)

    async def update(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        if self._session_extractor is not None:
            session = self._session_extractor(transaction_context)
            await self._execute_update(saga_data, session)

    async def delete(
        self,
        saga_data: SagaData,
        transaction_context: TransactionContext,
    ) -> None:
        if self._session_extractor is not None:
            session = self._session_extractor(transaction_context)
            await self._execute_delete(saga_data, session)

    async def _execute_insert(self, saga_data: SagaData, session: AsyncSession) -> None:
        data = self._convert_to_json_compatible(saga_data.data)
        await session.execute(
            insert(self._table).values(
                id=saga_data.id,
                revision=saga_data.revision,
                data=data,
                saga_type=type(saga_data.data).__name__,
            )
        )

    async def _execute_update(self, saga_data: SagaData, session: AsyncSession) -> None:
        data = self._convert_to_json_compatible(saga_data.data)
        result = await session.execute(
            update(self._table)
            .where(self._table.c.id == saga_data.id)
            .where(self._table.c.revision == saga_data.revision)
            .values(revision=saga_data.revision + 1, data=data),
        )
        if not result.rowcount:
            raise ConcurrencyExceptionError()

    async def _execute_delete(self, saga_data: SagaData, session: AsyncSession) -> None:
        await session.execute(delete(self._table).where(self._table.c.id == saga_data.id))

    def _convert_result(self, result: Any) -> SagaData:
        return SagaData(id=result.id, revision=result.revision, data=result.data)

    def _convert_to_json_compatible(self, data: Any) -> Any:
        if self._to_json_compatible:
            return self._to_json_compatible(data)

        return data
