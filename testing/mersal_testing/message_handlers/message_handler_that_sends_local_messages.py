from dataclasses import dataclass
from typing import Any

from mersal.app import Mersal

__all__ = (
    "MessageHandlerThatSendsLocalMessages",
    "MessageThatSendsAnotherMessage",
    "MessageThatSendsMultipleMessages",
)


@dataclass
class MessageThatSendsAnotherMessage:
    sent_message: Any


@dataclass
class MessageThatSendsMultipleMessages:
    sent_messages: list[Any]


class MessageHandlerThatSendsLocalMessages:
    def __init__(self, mersal: Mersal) -> None:
        self.mersal = mersal

    async def __call__(self, message: MessageThatSendsAnotherMessage | MessageThatSendsMultipleMessages) -> None:
        if isinstance(message, MessageThatSendsAnotherMessage):
            await self.mersal.send_local(message.sent_message)
        elif isinstance(message, MessageThatSendsMultipleMessages):
            for m in message.sent_messages:
                await self.mersal.send_local(m)
