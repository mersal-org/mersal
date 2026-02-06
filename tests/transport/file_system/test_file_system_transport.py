from typing import Any

import pytest

from mersal.transport.file_system import FileSystemTransport, FileSystemTransportConfig
from mersal_testing.transport.basic_transport_tests import (
    BasicTransportTest,
    TransportMaker,
)

__all__ = ("TestBasicTransportFunctionalityForFileSystemTransport",)


pytestmark = pytest.mark.anyio


class TestBasicTransportFunctionalityForFileSystemTransport(BasicTransportTest):
    @pytest.fixture
    def transport_maker(self, tmp_path) -> TransportMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        def maker(**kwargs: Any):
            input_queue_address = kwargs.get("input_queue_address", "default")
            return FileSystemTransport(
                FileSystemTransportConfig(base_directory=tmp_path, input_queue_address=input_queue_address)
            )

        return maker

    async def test_creates_queue_directory_on_call(self, tmp_path):
        config = FileSystemTransportConfig(base_directory=tmp_path, input_queue_address="my-queue")
        transport = FileSystemTransport(config)

        await transport()

        assert (tmp_path / "my-queue").is_dir()

    async def test_messages_are_persisted_as_json_files(self, transport_maker: TransportMaker):
        from mersal.transport import DefaultTransactionContext
        from mersal_testing.test_doubles import TransportMessageBuilder

        transport = transport_maker(input_queue_address="persist-test")
        message = TransportMessageBuilder.build()

        async with DefaultTransactionContext() as context:
            await transport.send("persist-test", message, context)
            context.set_result(commit=True, ack=True)
            await context.complete()

        queue_dir = transport._base_directory / "persist-test"
        files = list(queue_dir.glob("*.json"))
        assert len(files) == 1

    async def test_message_file_removed_after_receive(self, transport_maker: TransportMaker):
        from mersal.transport import DefaultTransactionContext
        from mersal_testing.test_doubles import TransportMessageBuilder

        transport = transport_maker(input_queue_address="remove-test")
        message = TransportMessageBuilder.build()

        async with DefaultTransactionContext() as context:
            await transport.send("remove-test", message, context)
            context.set_result(commit=True, ack=True)
            await context.complete()

        async with DefaultTransactionContext() as context:
            received = await transport.receive(context)
            assert received
            context.set_result(commit=True, ack=True)
            await context.complete()

        queue_dir = transport._base_directory / "remove-test"
        files = list(queue_dir.glob("*.json"))
        assert len(files) == 0
