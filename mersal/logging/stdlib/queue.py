import atexit
from logging import Handler, LogRecord, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any

__all__ = (
    "LoggingQueueListener",
    "QueueListenerHandler",
)


class LoggingQueueListener(QueueListener):
    def __init__(self, queue: Queue[LogRecord], *handlers: Handler, respect_handler_level: bool = False) -> None:
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self.start()
        atexit.register(self.stop)


class QueueListenerHandler(QueueHandler):
    """Listener/Handler for python < 3.12"""

    def __init__(self, handlers: list[Any] | None = None) -> None:
        """Initialize ``QueueListenerHandler``.

        Args:
            handlers: Optional 'ConvertingList'
        """
        super().__init__(Queue(-1))
        handlers = [handlers[i] for i in range(len(handlers))] if handlers else [StreamHandler()]
        self.listener = LoggingQueueListener(self.queue, *handlers)  # type: ignore[arg-type]
