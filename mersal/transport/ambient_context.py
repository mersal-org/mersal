from contextvars import ContextVar

from mersal.utils import Singleton

from .transaction_context import TransactionContext

__all__ = ("AmbientContext",)


_current_context: ContextVar[TransactionContext | None] = ContextVar("currentTransactionContext", default=None)


class AmbientContext(metaclass=Singleton):
    @property
    def current(self) -> TransactionContext | None:
        return _current_context.get()

    @current.setter
    def current(self, value: TransactionContext | None) -> None:
        _current_context.set(value)
