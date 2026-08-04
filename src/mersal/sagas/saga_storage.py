from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from mersal.sagas.correlation_property import CorrelationProperty
    from mersal.sagas.saga_data import SagaData
    from mersal.transport import TransactionContext

__all__ = ("SagaStorage",)


class SagaStorage(Protocol):
    async def __call__(self) -> None: ...

    async def find_using_id(self, saga_data_type: type, message_id: uuid.UUID) -> SagaData | None: ...

    async def find(self, saga_data_type: type, property_name: str, property_value: Any) -> SagaData | None: ...

    async def insert(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None: ...

    async def update(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None: ...

    async def delete(
        self,
        saga_data: SagaData,
        transaction_context: TransactionContext,
    ) -> None: ...
