from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeAlias, TypeVar

from mersal.pipeline import MessageContext
from mersal.unit_of_work.plugin import UnitOfWorkPlugin

__all__ = ("UnitOfWorkConfig",)


UnitOfWorkT = TypeVar("UnitOfWorkT")
UnitOfWorkFactory: TypeAlias = Callable[[MessageContext], Awaitable[UnitOfWorkT]]
UnitOfWorkCommitAction: TypeAlias = Callable[[MessageContext, UnitOfWorkT], Awaitable]
UnitOfWorkRollbackAction: TypeAlias = Callable[[MessageContext, UnitOfWorkT], Awaitable]
UnitOfWorkCloseAction: TypeAlias = Callable[[MessageContext, UnitOfWorkT], Awaitable]


@dataclass
class UnitOfWorkConfig:
    """Configuration for unit of work feature."""

    uow_factory: UnitOfWorkFactory
    """Callback to create the unit of work object.

    The callback is given :class:`MessageContext <.pipeline.MessageContext>` as an argument.
    This allows for creating custom unit of work objects depending on the message contents and/or headers.
    """
    commit_action: UnitOfWorkCommitAction
    """Action to run on commit."""
    rollback_action: UnitOfWorkRollbackAction
    """Action to run on callback."""
    close_action: UnitOfWorkCloseAction
    """Action to run on close and cleanup the unit of work object.

    Can be used to close database sessions for example.
    """
    commit_with_transaction: bool = False
    """
    Commit before or with the :class:`TransactionContext <.transport.TransactionContext>` commit.

    When `True`, the uow commit is part of the `TransactionContext` commit actions. This is required
    for the outbox and idempotency features to work.
    """

    @property
    def plugin(self) -> UnitOfWorkPlugin:
        return UnitOfWorkPlugin(self)
