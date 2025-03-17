from dataclasses import dataclass, field
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.outbox import OutboxConfig
from mersal.pipeline import MessageContext
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransportConfig,
)
from mersal_alchemy.sqlalchemy_outbox_storage import (
    SQLAlchemyOutboxStorageConfig,
)
from mersal_msgspec import MsgspecSerializer

__all__ = (
    "AddUser",
    "AddUserMessageHandler",
    "Base",
    "PromoteUser",
    "PromoteUserMessageHandler",
    "PromotedUsersRepo",
    "User",
    "app_factory",
)


@dataclass
class AddUser:
    username: str


@dataclass
class PromoteUser:
    username: str


NETWORK = InMemoryNetwork()


@dataclass
class PromotedUsersRepo:
    users: list[str] = field(default_factory=list)


PROMOTED_USERS = PromotedUsersRepo()


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
        session_factory: async_sessionmaker,
    ) -> None:
        self.mersal = mersal
        self.session = session_factory()
        transaction_context = message_context.transaction_context
        transaction_context.items["db-session"] = self.session

    async def __call__(self, message: AddUser) -> None:
        user = User(username=message.username)
        self.session.add(user)

        # Remember, do not commit session

        await self.mersal.send_local(PromoteUser(username=message.username))


class PromoteUserMessageHandler:
    async def __call__(self, message: PromoteUser) -> Any:
        # please don't do this in production
        PROMOTED_USERS.users.append(message.username)


async def app_factory() -> Mersal:
    engine = create_async_engine("sqlite+aiosqlite://", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine)

    outbox_storage = SQLAlchemyOutboxStorageConfig(
        async_session_factory=session_factory,
        table_name="outbox",
        session_extractor=lambda transaction_context: cast(AsyncSession, transaction_context.items.get("db-session")),
    ).storage
    queue_address = "test-queue"
    transport = InMemoryTransportConfig(network=NETWORK, input_queue_address=queue_address).transport
    activator = BuiltinHandlerActivator()
    activator.register(
        AddUser,
        lambda message_context, mersal: AddUserMessageHandler(
            mersal=mersal,
            message_context=message_context,
            session_factory=session_factory,
        ),
    )
    activator.register(
        PromoteUser,
        lambda _, __: PromoteUserMessageHandler(),
    )
    return Mersal(
        "m1",
        activator,
        transport=transport,
        outbox=OutboxConfig(storage=outbox_storage),
        message_body_serializer=MsgspecSerializer(object_types={AddUser, PromoteUser}),
    )
