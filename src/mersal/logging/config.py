from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from mersal.logging.logger import Logger

if TYPE_CHECKING:
    from mersal.plugins import Plugin

__all__ = ("LoggingConfig",)


GetLogger: TypeAlias = Callable[..., Logger]


@dataclass(kw_only=True)
class LoggingConfig:
    """Base Configuration for mersal's logging system."""

    logger_name: str = "mersal"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def plugin(self) -> Plugin:
        raise NotImplementedError("Need to implement a logging plugin for this config")

    def configure(self) -> GetLogger:
        raise NotImplementedError("Need to implement `configure` for this configuration")

    @staticmethod
    def set_level(logger: Logger, level: int) -> None:
        raise NotImplementedError("Need to implement `set_level` for this configuration")
