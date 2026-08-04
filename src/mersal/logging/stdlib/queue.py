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
        queue: Queue[LogRecord] = Queue(-1)
        super().__init__(queue)
        handlers = [handlers[i] for i in range(len(handlers))] if handlers else [StreamHandler()]
        self.listener = LoggingQueueListener(queue, *handlers)
