from typing import Any

__all__ = ("BatchMessage",)


class BatchMessage:
    def __init__(self, messages: list[Any]) -> None:
        self.messages = messages
