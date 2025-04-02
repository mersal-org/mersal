from typing import Any

from .message_headers import MessageHeaders

__all__ = ("TransportMessage",)


class TransportMessage:
    def __init__(self, body: Any, headers: MessageHeaders) -> None:
        self.headers = headers
        self.body = body

    @property
    def message_label(self) -> str:
        t = self.headers.message_type
        if not t:
            t = "unknown"
        return f"{t}/{self.headers.message_id}"
