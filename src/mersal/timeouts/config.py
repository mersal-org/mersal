from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mersal.configuration.standard_configurator import InvalidConfigurationError
from mersal.timeouts.plugin import TimeoutsPlugin

if TYPE_CHECKING:
    from mersal.timeouts.timeout_manager import TimeoutManager

__all__ = ("TimeoutsConfig",)


@dataclass
class TimeoutsConfig:
    """Configuration for deferred messages on transports without native deferral.

    Exactly one of `storage` and `external_timeout_manager_address` must be set.
    """

    storage: TimeoutManager | None = None
    """Makes this app a timeout manager. Deferred messages are sent to this app's own
    address, stored here and sent to their recipient once due."""
    external_timeout_manager_address: str | None = None
    """Address of another app that hosts the timeout manager. Deferred messages
    (including ones this app receives) are sent there."""
    poll_interval: float = 1
    """Seconds between checks for due messages (only with `storage`)."""

    def __post_init__(self) -> None:
        if (self.storage is None) == (self.external_timeout_manager_address is None):
            raise InvalidConfigurationError(
                "TimeoutsConfig needs exactly one of storage and external_timeout_manager_address"
            )

    @property
    def plugin(self) -> TimeoutsPlugin:
        return TimeoutsPlugin(self)
