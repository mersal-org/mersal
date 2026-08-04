from mersal.messages import TransportMessage
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.incoming_step_context import IncomingStepContext
from mersal.serialization import MessageSerializer
from mersal.types import AsyncAnyCallable

__all__ = ("DeserializeIncomingMessageStep",)


class DeserializeIncomingMessageStep(IncomingStep):
    def __init__(self, serializer: MessageSerializer):
        self.serializer = serializer

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transport_message = context.load(TransportMessage)

        message = await self.serializer.deserialize(transport_message)

        context.save(message)

        await next_step()
