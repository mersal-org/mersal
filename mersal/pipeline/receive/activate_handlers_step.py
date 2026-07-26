from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mersal.messages import BatchMessage, LogicalMessage
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
from mersal.transport import TransactionContext

if TYPE_CHECKING:
    from mersal.activation import HandlerActivator
    from mersal.pipeline.incoming_step_context import IncomingStepContext
    from mersal.types import AsyncAnyCallable

__all__ = ("ActivateHandlersStep",)


@dataclass
class _HandlerWithMessage:
    message: Any
    handler: Any


class ActivateHandlersStep(IncomingStep):
    def __init__(self, handler_activator: HandlerActivator) -> None:
        self.handler_activator = handler_activator

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
        logical_message = context.load(LogicalMessage)
        message = logical_message.body
        handlers_with_message: list[_HandlerWithMessage] = []

        messages = message.messages if isinstance(message, BatchMessage) else [message]

        for m in messages:
            handlers_with_message.extend(
                [
                    _HandlerWithMessage(m, handler)
                    for handler in await self.handler_activator.get_handlers(m, transaction_context)
                ]
            )
        _handler_invokers: list[HandlerInvoker | SagaHandlerInvoker] = []
        for _handler_with_message in handlers_with_message:

            async def action(_handler_with_message: _HandlerWithMessage = _handler_with_message) -> None:
                _handler = _handler_with_message.handler
                _message = _handler_with_message.message
                await _handler(_message)

            handler_invoker = HandlerInvoker(
                action,
                _handler_with_message.handler,
                transaction_context,
            )

            from mersal.sagas.saga import SagaBase

            if isinstance(_handler_with_message.handler, SagaBase):
                invoker = SagaHandlerInvoker(_handler_with_message.handler, handler_invoker)
                _handler_invokers.append(invoker)
            else:
                _handler_invokers.append(handler_invoker)

        handler_invokers = HandlerInvokers(logical_message, _handler_invokers)
        context.save(handler_invokers)
        await next_step()
