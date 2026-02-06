import uuid

import pytest

from mersal.persistence.file_system import FileSystemMessageTracker
from mersal.transport import DefaultTransactionContext

__all__ = ("TestFileSystemMessageTracker",)


pytestmark = pytest.mark.anyio


class TestFileSystemMessageTracker:
    async def test_track_and_check(self, tmp_path):
        tracker = FileSystemMessageTracker(tmp_path)
        message_id = uuid.uuid4()

        async with DefaultTransactionContext() as ctx:
            assert not await tracker.is_message_tracked(message_id, ctx)
            await tracker.track_message(message_id, ctx)
            assert await tracker.is_message_tracked(message_id, ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

    async def test_untracked_message_returns_false(self, tmp_path):
        tracker = FileSystemMessageTracker(tmp_path)

        async with DefaultTransactionContext() as ctx:
            assert not await tracker.is_message_tracked(uuid.uuid4(), ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

    async def test_data_persists_across_instances(self, tmp_path):
        tracker1 = FileSystemMessageTracker(tmp_path)
        message_id = uuid.uuid4()

        async with DefaultTransactionContext() as ctx:
            await tracker1.track_message(message_id, ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()

        tracker2 = FileSystemMessageTracker(tmp_path)

        async with DefaultTransactionContext() as ctx:
            assert await tracker2.is_message_tracked(message_id, ctx)
            ctx.set_result(commit=True, ack=True)
            await ctx.complete()
