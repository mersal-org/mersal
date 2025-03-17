import uuid
from collections.abc import Callable
from typing import Any, Protocol

from mersal.messages import LogicalMessage
from mersal.pipeline.outgoing_step_context import OutgoingStepContext

__all__ = (
    "MessageIdGenerator",
    "SetDefaultHeadersStep",
)


class MessageIdGenerator(Protocol):
    """Generate a message id given the message instance."""

    def __call__(self, message: LogicalMessage) -> Any: ...


class SetDefaultHeadersStep:
    """A send step to inject default message headers if they don't exist."""

    def __init__(self, message_id_generator: MessageIdGenerator | None = None):
        self.message_id_generator = message_id_generator if message_id_generator else lambda _: uuid.uuid4()

    async def __call__(self, context: OutgoingStepContext, next_step: Callable) -> None:
        logical_message: LogicalMessage = context.load(LogicalMessage)
        headers = logical_message.headers

        if not headers.get("message_id"):
            headers["message_id"] = self.message_id_generator(logical_message)

        await next_step()
