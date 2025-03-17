from dataclasses import dataclass

from mersal.outbox.outbox_storage import OutboxStorage

__all__ = ("OutboxConfig",)


@dataclass
class OutboxConfig:
    """Configuration for the outbox feature."""

    storage: OutboxStorage
    "Sets the Outbox storage."
