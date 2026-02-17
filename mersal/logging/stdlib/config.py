import sys
from dataclasses import dataclass, field
from logging.config import dictConfig
from typing import Any

from mersal.logging.config import GetLogger, LoggingConfig
from mersal.logging.logger import Logger
from mersal.logging.standard_plugin import StandardLoggingPlugin
from mersal.logging.stdlib.logger import StdlibLogger
from mersal.plugins import Plugin

__all__ = ("StdlibLoggingConfig",)


@dataclass(kw_only=True)
class StdlibLoggingConfig(LoggingConfig):
    formatters: dict[str, dict[str, Any]] = field(default_factory=dict)
    handlers: dict[str, dict[str, Any]] = field(default_factory=dict)
    loggers: dict[str, dict[str, Any]] = field(default_factory=dict)
    root: dict[str, Any] = field(default_factory=dict)
    configure_root_logger: bool = field(default=True)

    def __post_init__(self):
        if "standard" not in self.formatters:
            self.formatters["standard"] = self._standard_formatter()

        if "console" not in self.handlers:
            self.handlers["console"] = self._default_console_handler()

        if "queue_listener" not in self.handlers:
            self.handlers["queue_listener"] = self._default_queue_listener_handler()

        if "mersal" not in self.loggers:
            self.loggers["mersal"] = self._get_mersal_logger()

        if not self.root:
            self.root = {
                "handlers": ["queue_listener"],
                "level": "INFO",
            }

    @property
    def plugin(self) -> Plugin:
        return StandardLoggingPlugin(config=self)

    def configure(self) -> GetLogger:
        logger_config: dict[str, Any] = {}

        logger_config["formatters"] = self.formatters
        logger_config["handlers"] = self.handlers
        logger_config["loggers"] = self.loggers

        if self.configure_root_logger:
            logger_config["root"] = self.root

        dictConfig(logger_config)
        return lambda: StdlibLogger()  # noqa: PLW0108

    @staticmethod
    def set_level(logger: Logger, level: int) -> None:
        logger.set_level(level)

    def _standard_formatter(self) -> dict[str, Any]:
        return {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}

    def _default_console_handler(self) -> dict[str, Any]:
        return {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        }

    def _default_queue_listener_handler(self) -> dict[str, Any]:
        if sys.version_info >= (3, 12):
            return {
                "class": "logging.handlers.QueueHandler",
                "level": "DEBUG",
                "queue": {
                    "()": "queue.Queue",
                    "maxsize": -1,
                },
                "listener": "mersal.logging.queue.LoggingQueueListener",
                "handlers": ["console"],
            }
        return {
            "class": "mersal.logging.queue.QueueListenerHandler",
            "level": "DEBUG",
            "formatter": "standard",
        }

    def _get_mersal_logger(self) -> dict[str, Any]:
        return {"level": "INFO", "handlers": ["queue_listener"], "propagate": False}
