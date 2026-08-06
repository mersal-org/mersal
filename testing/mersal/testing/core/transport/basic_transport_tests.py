import itertools
from typing import Any, Protocol

import anyio
import pytest

from mersal.messages import TransportMessage
from mersal.testing.core.test_doubles import TransportMessageBuilder
from mersal.transport import DefaultTransactionContext, Transport
from mersal.types.callable_types import AsyncAnyCallable

__all__ = (
    "BasicTransportTest",
    "TransportMaker",
)


pytestmark = pytest.mark.anyio


class TransportMaker(Protocol):
    def __call__(self, **kwargs: Any) -> Transport: ...


# This suite always calls `await transport()` right after constructing each transport,
# before it's addressed as a send destination - mirroring how a real app starts a
# transport before anything can reach it. In-memory/file-backed transports don't
# strictly need this (there's no broker-side queue to declare), but broker-backed ones
# (e.g. RabbitMQ) do: without it, sending to a transport that hasn't started yet would
# hit a destination that doesn't exist server-side.


class BasicTransportTest:
    #: Deadline for a receive that is expected to produce a message. Generous, since a
    #: correct transport returns as soon as the message arrives; it only fires (failing
    #: the test with a `TimeoutError`) when delivery is genuinely broken - the
    #: alternative being a test that hangs forever.
    receive_timeout: float = 5.0

    #: How long a receive on a queue expected to be empty is given before the suite
    #: concludes that no message is coming. Only transports whose `receive` blocks
    #: until a message arrives (e.g. broker-backed push consumers) ever wait this
    #: long; transports that return `None` immediately never touch it.
    empty_receive_timeout: float = 0.5

    @pytest.fixture
    def transport_maker(self) -> TransportMaker:
        def maker(**kwargs: Any) -> Transport:
            raise NotImplementedError()

        return maker

    async def receive(
        self,
        transport: Transport,
        context: DefaultTransactionContext,
        *,
        expect_empty: bool = False,
    ) -> TransportMessage | None:
        """Call `transport.receive` with a deadline instead of trusting it to return.

        The transport contract allows `receive` to block until a message shows up -
        broker-backed push consumers do exactly that; only in-memory-style transports
        return `None` immediately. The suite therefore never calls `receive` bare: the
        deadline is what turns "blocks forever" into either a fast failure (a message
        was expected) or an empty-queue verdict (none was).
        """
        if expect_empty:
            with anyio.move_on_after(self.empty_receive_timeout):
                return await transport.receive(context)
            return None
        with anyio.fail_after(self.receive_timeout):
            return await transport.receive(context)

    async def assert_with_context(
        self,
        assertions_call: AsyncAnyCallable,
        commit: bool = True,
        ack: bool = True,
        complete: bool = True,
    ) -> None:
        async with DefaultTransactionContext() as context:
            await assertions_call(context)
            context.set_result(commit=commit, ack=ack)
            if complete:
                await context.complete()

    async def test_empty_queue_returns_none_for_receive(self, transport_maker: TransportMaker) -> None:
        """When a queue is empty, invoking the `receive` method should return `None`."""
        transport = transport_maker(input_queue_address="moon")
        await transport()

        async def _assert(context: DefaultTransactionContext) -> None:
            transport_message = await self.receive(transport, context, expect_empty=True)
            assert not transport_message

        await self.assert_with_context(_assert)

    async def test_can_send_and_receive(self, transport_maker: TransportMaker) -> None:
        """Simple sending of two messages and asserting they are received."""
        transport1_address = "ad1"
        transport2_address = "ad2"
        transport1 = transport_maker(input_queue_address=transport1_address)
        transport2 = transport_maker(input_queue_address=transport2_address)
        await transport1()
        await transport2()
        transport_message1 = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message1, context)
            await transport1.send(transport2_address, transport_message2, context)

        await self.assert_with_context(_assert1)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message1 = await self.receive(transport2, context)
            received_message2 = await self.receive(transport2, context)
            received_message3 = await self.receive(transport2, context, expect_empty=True)
            assert received_message1
            assert received_message2
            received_ids = {str(received_message1.headers.message_id), str(received_message2.headers.message_id)}
            expected_ids = {str(transport_message1.headers.message_id), str(transport_message2.headers.message_id)}
            assert received_ids == expected_ids
            assert not received_message3

        await self.assert_with_context(_assert2)

    @pytest.mark.parametrize("should_ack", [True, False])
    async def test_should_not_send_outgoing_messages_without_committing_transaction(
        self,
        transport_maker: TransportMaker,
        should_ack: bool,
    ) -> None:
        transport1_address = "ad1"
        transport2_address = "ad2"
        transport1 = transport_maker(input_queue_address=transport1_address)
        transport2 = transport_maker(input_queue_address=transport2_address)
        await transport1()
        await transport2()
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1, commit=False, ack=should_ack)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await self.receive(transport2, context, expect_empty=True)
            assert not received_message

        await self.assert_with_context(_assert2)

    @pytest.mark.parametrize("should_ack", [True, False])
    async def test_should_send_outgoing_messages_after_committing_transaction(
        self,
        transport_maker: TransportMaker,
        should_ack: bool,
    ) -> None:
        transport1_address = "ad1"
        transport2_address = "ad2"
        transport1 = transport_maker(input_queue_address=transport1_address)
        transport2 = transport_maker(input_queue_address=transport2_address)
        await transport1()
        await transport2()
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1, commit=True, ack=should_ack)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await self.receive(transport2, context)
            assert received_message

        await self.assert_with_context(_assert2)

    @pytest.mark.parametrize(
        ["should_commit_first_time", "should_commit_second_time", "should_complete"],
        itertools.combinations([True, False, True], 3),
    )
    async def test_return_message_to_queue_if_receive_transaction_nacked(
        self,
        transport_maker: TransportMaker,
        should_commit_first_time: bool,
        should_commit_second_time: bool,
        should_complete: bool,
    ) -> None:
        transport1_address = "ad1"
        transport2_address = "ad2"
        transport1 = transport_maker(input_queue_address=transport1_address)
        transport2 = transport_maker(input_queue_address=transport2_address)
        await transport1()
        await transport2()
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await self.receive(transport2, context)
            assert received_message
            assert str(received_message.headers.message_id) == str(transport_message.headers.message_id)

        await self.assert_with_context(
            _assert2,
            commit=should_commit_first_time,
            ack=False,
            complete=should_complete,
        )

        async def _assert3(context: DefaultTransactionContext) -> None:
            received_message = await self.receive(transport2, context)
            assert received_message
            assert str(received_message.headers.message_id) == str(transport_message.headers.message_id)

        await self.assert_with_context(_assert3, commit=should_commit_second_time, ack=True)

        async def _assert4(context: DefaultTransactionContext) -> None:
            received_message = await self.receive(transport2, context, expect_empty=True)
            assert not received_message

        await self.assert_with_context(_assert4)
