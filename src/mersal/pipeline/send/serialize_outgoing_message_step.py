from collections.abc import Callable

from mersal.messages import LogicalMessage
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.serialization import MessageSerializer

__all__ = ("SerializeOutgoingMessageStep",)


class SerializeOutgoingMessageStep:
    def __init__(self, serializer: MessageSerializer):
        self.serializer = serializer

    async def __call__(self, context: OutgoingStepContext, next_step: Callable) -> None:
        logical_message = context.load(LogicalMessage)
        transport_message = await self.serializer.serialize(logical_message)
        context.save(transport_message)

        await next_step()
