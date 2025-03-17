from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mersal.exceptions.base_exceptions import (
    ConcurrencyExceptionError,
    MersalExceptionError,
)
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.message_context import MessageContext
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
from mersal.transport.transaction_context import TransactionContext

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from mersal.pipeline import IncomingStepContext
    from mersal.sagas.correlation_error_handler import CorrelationErrorHandler
    from mersal.sagas.correlation_property import CorrelationProperty
    from mersal.sagas.saga import Saga
    from mersal.sagas.saga_data import SagaData
    from mersal.sagas.saga_storage import SagaStorage
    from mersal.types import AsyncAnyCallable

__all__ = (
    "LoadSagaDataStep",
    "SagasOperationWrapper",
)


@dataclass
class SagasOperationWrapper:
    saga_data: SagaData
    correlation_properties: Sequence[CorrelationProperty]
    saga: Saga


class LoadSagaDataStep(IncomingStep):
    def __init__(
        self,
        saga_storage: SagaStorage,
        correlation_error_handler: CorrelationErrorHandler,
    ) -> None:
        self.correlation_error_handler = correlation_error_handler
        self.saga_storage = saga_storage

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        handler_invokers = context.load(HandlerInvokers)
        transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
        messaage = handler_invokers.message
        message_type = type(messaage.body)
        saga_invokers: Iterable[SagaHandlerInvoker] = filter(
            lambda invoker: isinstance(invoker, SagaHandlerInvoker),
            handler_invokers,
        )
        loaded_sagas: list[SagasOperationWrapper] = []
        created_sagas: list[SagasOperationWrapper] = []
        for saga_invoker in saga_invokers:
            saga = saga_invoker.saga
            message_correlation_properties = [
                cr for cr in saga.correlation_properties if cr.message_type is message_type
            ]
            found_existing_data = await self._try_to_find_existing_saga(
                saga, message_correlation_properties, transaction_context
            )

            if not found_existing_data:
                if message_type in saga.initiating_message_types:
                    saga.data = saga.generate_new_data()
                    created_sagas.append(SagasOperationWrapper(saga.data, message_correlation_properties, saga))
                else:
                    await self.correlation_error_handler(saga.correlation_properties, saga_invoker, messaage)
            else:
                loaded_sagas.append(SagasOperationWrapper(saga.data, message_correlation_properties, saga))
        await next_step()
        sagas_to_update = [s for s in loaded_sagas if not s.saga.is_completed and not s.saga.is_unchanged]
        for d in sagas_to_update:
            await self._save_saga_data(d, insert=False, transaction_context=transaction_context)
        sagas_to_insert = [s for s in created_sagas if not s.saga.is_completed]
        for d in sagas_to_insert:
            await self._save_saga_data(d, insert=True, transaction_context=transaction_context)
        sagas_to_delete = [s for s in loaded_sagas if s.saga.is_completed]
        for s in sagas_to_delete:
            await self.saga_storage.delete(s.saga_data, transaction_context)

    async def _try_to_find_existing_saga(
        self,
        saga: Saga,
        message_correlation_properties: Iterable[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> bool:
        for correlation_property in message_correlation_properties:
            matching_message_value = correlation_property.value_extractor(MessageContext(transaction_context))
            saga_data = await self.saga_storage.find(
                saga.data_type,
                correlation_property.property_name,
                matching_message_value,
            )
            if not saga_data:
                continue

            saga.data = saga_data
            return True

        return False

    async def _save_saga_data(
        self,
        data: SagasOperationWrapper,
        insert: bool,
        transaction_context: TransactionContext,
    ) -> None:
        saga_data = data.saga_data
        correlation_properties = data.correlation_properties
        saga = data.saga
        attempts = 0
        while attempts < 5:
            attempts += 1
            try:
                if insert:
                    await self.saga_storage.insert(saga_data, correlation_properties, transaction_context)
                    return

                await self.saga_storage.update(saga_data, correlation_properties, transaction_context)
                return
            except ConcurrencyExceptionError:
                fresh_data = await self.saga_storage.find_using_id(saga.data_type, saga_data.id)
                if not fresh_data:
                    raise MersalExceptionError("Couldn't find SagaData") from None

                await saga.resolve_conflict(fresh_data)
                saga_data.revision = fresh_data.revision
