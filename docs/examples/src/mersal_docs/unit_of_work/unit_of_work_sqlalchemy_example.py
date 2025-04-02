from dataclasses import dataclass

from mersal_alchemy import (
    SQLAlchemyUnitOfWork,
    default_sqlalchemy_close_action,
    default_sqlalchemy_commit_action,
    default_sqlalchemy_rollback_action,
)
from mersal_msgspec import MsgspecSerializer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.pipeline import MessageContext
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransportConfig,
)
from mersal.unit_of_work import UnitOfWorkConfig

__all__ = (
    "AddUser",
    "AddUserMessageHandler",
    "Base",
    "User",
    "app_factory",
)


@dataclass
class AddUser:
    username: str


NETWORK = InMemoryNetwork()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(primary_key=True)


class AddUserMessageHandler:
    def __init__(
        self,
        mersal: Mersal,
        message_context: MessageContext,
    ) -> None:
        self.mersal = mersal
        transaction_context = message_context.transaction_context
        uow: SQLAlchemyUnitOfWork = transaction_context.items["uow"]
        self.session = uow.session

    async def __call__(self, message: AddUser) -> None:
        user = User(username=message.username)
        self.session.add(user)
        # Remember, do not commit uow or session here


engine = create_async_engine("sqlite+aiosqlite://", echo=True)


async def app_factory() -> Mersal:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine)

    async def uow_factory(_: MessageContext) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(async_session_maker=session_factory)

    unit_of_work = UnitOfWorkConfig(
        uow_factory=uow_factory,
        commit_action=default_sqlalchemy_commit_action,
        rollback_action=default_sqlalchemy_rollback_action,
        close_action=default_sqlalchemy_close_action,
    )
    queue_address = "test-queue"
    transport = InMemoryTransportConfig(network=NETWORK, input_queue_address=queue_address).transport
    activator = BuiltinHandlerActivator()
    activator.register(
        AddUser,
        lambda message_context, mersal: AddUserMessageHandler(
            mersal=mersal,
            message_context=message_context,
        ),
    )
    return Mersal(
        "m1",
        activator,
        transport=transport,
        unit_of_work=unit_of_work,
        message_body_serializer=MsgspecSerializer(object_types={AddUser}),
    )
