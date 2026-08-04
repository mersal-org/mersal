from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mersal.idempotency.plugin import IdempotencyPlugin

if TYPE_CHECKING:
    from mersal.idempotency.message_tracker import MessageTracker

__all__ = ("IdempotencyConfig",)


@dataclass
class IdempotencyConfig:
    """Configuration for idempotency."""

    tracker: MessageTracker
    """Message tracking persistence mechanism."""
    should_stop_invocation: bool
    """Whether to run message handlers for repeated messages or not."""

    @property
    def plugin(self) -> IdempotencyPlugin:
        return IdempotencyPlugin(self)
