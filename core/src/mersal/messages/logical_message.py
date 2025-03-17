from typing import Any

from .message_headers import MessageHeaders

__all__ = ("LogicalMessage",)


class LogicalMessage:
    def __init__(self, body: Any, headers: MessageHeaders) -> None:
        self.headers = headers
        self.body = body

    @property
    def message_label(self) -> str:
        t = self.headers.message_type
        if not t:
            t = str(type(self.body))
        return f"{t}/{self.headers.message_id}"
