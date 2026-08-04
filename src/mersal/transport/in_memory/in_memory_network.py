from collections import defaultdict, deque

from mersal.messages import TransportMessage

__all__ = ("InMemoryNetwork",)


class InMemoryNetwork:
    def __init__(self) -> None:
        self._queues: dict[str, deque[TransportMessage]] = defaultdict(deque)

    def reset(self) -> None:
        self._queues.clear()

    def count(self) -> int:
        return sum([len(x) for x in self._queues.values()])

    def queue_count(self, input_queue_name: str) -> int:
        return len(self._queues[input_queue_name])

    def deliver(self, destination_address: str, message: TransportMessage) -> None:
        self._queues[destination_address].appendleft(message)

    def get_next(self, input_queue_name: str) -> TransportMessage | None:
        try:
            return self._queues[input_queue_name].pop()
        except IndexError:
            return None

    def create_queue(self, address: str) -> None:
        # it's a default dict!
        self._queues[address]
