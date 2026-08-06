from typing import Any

__all__ = ("UnitOfWorkTestHelper",)


class UnitOfWorkTestHelper:
    def __init__(self) -> None:
        self.committed = 0
        self.rollbacked = 0
        self.closed = 0
        self.message_context: Any = None

    async def uow_factory(self, message_context: Any) -> "UnitOfWorkTestHelper":
        self.message_context = message_context
        return self

    async def commit_action(self, message_context: Any, uow: Any) -> None:
        self.committed += 1

    async def rollback_action(self, message_context: Any, uow: Any) -> None:
        self.rollbacked += 1

    async def close_action(self, message_context: Any, uow: Any) -> None:
        self.closed += 1
