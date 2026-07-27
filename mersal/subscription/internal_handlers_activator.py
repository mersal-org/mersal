from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from mersal.messages.control import SubscribeRequest, UnsubscribeRequest
from mersal.subscription.handlers import SubscribeRequestHandler, UnsubscribeRequestHandler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal.activation import HandlerActivator, HandlerFactory
    from mersal.app import Mersal
    from mersal.handlers import MessageHandler
    from mersal.subscription.subscription_storage import SubscriptionStorage
    from mersal.transport import TransactionContext

MessageT = TypeVar("MessageT")

__all__ = ("InternalHandlersActivator",)


class InternalHandlersActivator:
    """Decorates a `HandlerActivator` with Mersal's own control-message handlers.

    Registers handlers for `SubscribeRequest`/`UnsubscribeRequest` so that any app
    can act as the owner (publisher) of a topic when subscription storage is decentralized.
    """

    def __init__(self, inner: HandlerActivator, subscription_storage: SubscriptionStorage) -> None:
        self._inner = inner
        self._internal_handlers: dict[type, list[MessageHandler]] = {
            SubscribeRequest: [SubscribeRequestHandler(subscription_storage)],
            UnsubscribeRequest: [UnsubscribeRequestHandler(subscription_storage)],
        }

    async def get_handlers(
        self,
        message: MessageT,
        transaction_context: TransactionContext,
    ) -> Sequence[MessageHandler[MessageT]]:
        own_handlers = self._internal_handlers.get(type(message), [])
        handlers = await self._inner.get_handlers(message, transaction_context)
        return [*handlers, *own_handlers]

    def register(
        self,
        message_type: type[MessageT],
        factory: HandlerFactory[MessageT],
    ) -> InternalHandlersActivator:
        self._inner.register(message_type, factory)
        return self

    @property
    def registered_message_types(self) -> set[type]:
        return self._inner.registered_message_types

    @property
    def app(self) -> Mersal:
        return self._inner.app

    @app.setter
    def app(self, value: Mersal) -> None:
        self._inner.app = value
