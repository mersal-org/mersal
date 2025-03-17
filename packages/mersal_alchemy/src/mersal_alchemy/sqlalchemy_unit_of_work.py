from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mersal.pipeline.message_context import MessageContext

__all__ = (
    "SQLAlchemyUnitOfWork",
    "default_sqlalchemy_close_action",
    "default_sqlalchemy_commit_action",
    "default_sqlalchemy_rollback_action",
)


class SQLAlchemyUnitOfWork:
    """A unit of work class for SQLAlchemy."""

    def __init__(self, async_session_maker: async_sessionmaker[AsyncSession]) -> None:
        """Initializes SQLAlchemyUnitOfWork.

        Args:
            async_session_maker: session factory.
        """
        self._async_session_maker = async_session_maker
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session:
            return self._session

        self._session = self._async_session_maker()
        return self._session

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()

    async def close(self) -> None:
        if self._session:
            await self._session.close()


async def default_sqlalchemy_commit_action(_: MessageContext, uow: SQLAlchemyUnitOfWork) -> None:
    """Helper function for SQLAalchemyUnitOfWork commit"""
    await uow.commit()


async def default_sqlalchemy_rollback_action(_: MessageContext, uow: SQLAlchemyUnitOfWork) -> None:
    """Helper function for SQLAalchemyUnitOfWork rollback"""
    await uow.rollback()


async def default_sqlalchemy_close_action(_: MessageContext, uow: SQLAlchemyUnitOfWork) -> None:
    """Helper function for SQLAalchemyUnitOfWork close"""
    await uow.close()
