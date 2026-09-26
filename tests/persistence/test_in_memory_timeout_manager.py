from datetime import UTC, datetime, timedelta

import pytest

from mersal.persistence.in_memory import InMemoryTimeoutManager
from mersal.testing.core.test_doubles import TransportMessageBuilder

__all__ = ("TestInMemoryTimeoutManager",)


pytestmark = pytest.mark.anyio


class TestInMemoryTimeoutManager:
    async def test_provides_only_due_messages_ordered_by_due_time(self):
        subject = InMemoryTimeoutManager()
        now = datetime.now(UTC)
        later = TransportMessageBuilder.build()
        earlier = TransportMessageBuilder.build()
        future = TransportMessageBuilder.build()
        await subject.defer(now - timedelta(seconds=1), later)
        await subject.defer(now - timedelta(seconds=2), earlier)
        await subject.defer(now + timedelta(minutes=1), future)

        async with subject.get_due_messages() as due_messages:
            ids = [x.message.headers.message_id for x in due_messages]

        assert ids == [earlier.headers.message_id, later.headers.message_id]

    async def test_only_completed_messages_are_removed(self):
        subject = InMemoryTimeoutManager()
        past = datetime.now(UTC) - timedelta(seconds=1)
        first = TransportMessageBuilder.build()
        await subject.defer(past, first)
        await subject.defer(past, TransportMessageBuilder.build())

        async with subject.get_due_messages() as due_messages:
            await due_messages[0].mark_as_completed()

        assert len(subject) == 1
        async with subject.get_due_messages() as due_messages:
            assert len(due_messages) == 1
            assert due_messages[0].message.headers.message_id != first.headers.message_id
