from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from mersal.exceptions.base_exceptions import ConcurrencyExceptionError
from mersal.sagas.saga_storage import SagaStorage

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from mersal.sagas import CorrelationProperty, SagaData
    from mersal.transport import TransactionContext

__all__ = ("InMemorySagaStorage",)


class InMemorySagaStorage(SagaStorage):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, SagaData] = {}

    async def __call__(self) -> None:
        self._store = {}

    async def find_using_id(self, saga_data_type: type, message_id: uuid.UUID) -> SagaData | None:
        return self._store.get(message_id)

    async def find(self, saga_data_type: type, property_name: str, property_value: Any) -> SagaData | None:
        for data in self._store.values():
            if type(data.data) is not saga_data_type:
                continue

            if hasattr(data.data, property_name) and getattr(data.data, property_name) == property_value:
                return deepcopy(data)

        return None

    async def insert(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        if self._store.get(saga_data.id):
            raise Exception("SagaData already exist")

        self._verify_correllation_properties_uniqueness(saga_data, correlation_properties)
        if saga_data.revision != 0:
            raise Exception("Inserted data must have revision=0")

        self._store[saga_data.id] = deepcopy(saga_data)

    async def update(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        self._verify_correllation_properties_uniqueness(saga_data, correlation_properties)
        current_saga_data = self._store.get(saga_data.id)
        if not current_saga_data:
            raise Exception("Saga couldn't be found")

        if not current_saga_data.revision == saga_data.revision:
            raise ConcurrencyExceptionError("Concurrency issues, different revisios")

        _copy = deepcopy(saga_data)
        _copy.revision += 1
        self._store[saga_data.id] = _copy
        saga_data.revision += 1

    async def delete(self, saga_data: SagaData, transaction_context: TransactionContext) -> None:
        if self._store.get(saga_data.id):
            del self._store[saga_data.id]

        saga_data.revision += 1

    def _verify_correllation_properties_uniqueness(
        self,
        new_or_updated_saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
    ) -> None:
        for existing_saga_data in self._store.values():
            if existing_saga_data.id == new_or_updated_saga_data.id:
                continue

            if type(existing_saga_data) is type(new_or_updated_saga_data):
                continue

            for correlation_property in correlation_properties:
                property_name = correlation_property.property_name
                new_value = getattr(new_or_updated_saga_data.data, property_name)
                if hasattr(existing_saga_data.data, property_name):
                    existing_value = getattr(existing_saga_data.data, property_name)

                    if existing_value == new_value:
                        raise Exception("Correlation properties are not unique!")
