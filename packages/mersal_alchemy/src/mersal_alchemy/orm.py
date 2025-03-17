import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Identity,
    Integer,
    LargeBinary,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import registry
from sqlalchemy.types import JSON

__all__ = (
    "create_outbox_table_and_map",
    "create_sagas_table",
)


JsonB = JSON().with_variant(PG_JSONB, "postgresql")


def create_outbox_table_and_map(
    table_name: str,
    mapper_registry: registry,
) -> Table:
    metadata = mapper_registry.metadata
    table: Table | None = None
    for _table in metadata.sorted_tables:
        if _table.name == table_name:
            table = _table
            break
    if table is None:
        table = Table(
            table_name,
            metadata,
            Column(
                "outbox_message_id",
                BigInteger().with_variant(Integer, "sqlite"),
                Identity(always=True, start=1),
                primary_key=True,
            ),
            Column("destination_address", String, nullable=False),
            Column("body", LargeBinary, nullable=False),
            Column("headers", LargeBinary, nullable=False),
            Column("sent", Boolean, nullable=False, default=False),
        )

    return table


def create_sagas_table(table_name: str, mapper_registry: registry) -> Table:
    metadata = mapper_registry.metadata
    table: Table | None = None
    for _table in metadata.sorted_tables:
        if _table.name == table_name:
            table = _table
            break
    if table is None:
        table = Table(
            table_name,
            metadata,
            Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column("revision", Integer, nullable=False),
            Column("data", JsonB, nullable=False),
            Column("saga_type", String, nullable=False),
        )

    return table
