import uuid

from anyio import Event

from .poller import Poller, PollingResult

__all__ = ("DefaultPoller",)


class DefaultPoller(Poller):
    def __init__(self) -> None:
        self.results: dict[uuid.UUID, PollingResult] = {}
        self.events: dict[uuid.UUID, Event] = {}

    async def poll(self, message_id: uuid.UUID) -> PollingResult:
        # Check if result already exists
        message = self.results.get(message_id)
        if message:
            return message

        # Create an event for this message_id if it doesn't exist
        if message_id not in self.events:
            self.events[message_id] = Event()

        # Wait for the event to be set
        await self.events[message_id].wait()

        # Return the result (should be available now)
        return self.results[message_id]

    async def push(self, message_id: uuid.UUID, exception: Exception | None = None) -> None:
        # Store the result
        self.results[message_id] = PollingResult(message_id, exception)

        # If there's a waiting event, trigger it
        if message_id in self.events:
            self.events[message_id].set()
