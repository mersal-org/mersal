import itertools
from typing import Any, Protocol

import pytest

from mersal.transport import DefaultTransactionContext, Transport
from mersal.types.callable_types import AsyncAnyCallable
from mersal_testing.test_doubles import TransportMessageBuilder

__all__ = (
    "BasicTransportTest",
    "TransportMaker",
)


pytestmark = pytest.mark.anyio


class TransportMaker(Protocol):
    def __call__(self, **kwargs: Any) -> Transport: ...


class BasicTransportTest:
    @pytest.fixture
    def transport_maker(self) -> TransportMaker:
        def maker(**kwargs: Any) -> Transport:
            raise NotImplementedError()

        return maker

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
        transport = transport_maker(input_queue_address="moon")

        async def _assert(context: DefaultTransactionContext) -> None:
            transport_message = await transport.receive(context)
            assert not transport_message

        await self.assert_with_context(_assert)

    async def test_can_send_and_receive(self, transport_maker: TransportMaker) -> None:
        transport1_address = "ad1"
        transport2_address = "ad2"
        transport1 = transport_maker(input_queue_address=transport1_address)
        transport2 = transport_maker(input_queue_address=transport2_address)
        transport_message1 = TransportMessageBuilder.build()
        transport_message2 = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message1, context)
            await transport1.send(transport2_address, transport_message2, context)

        await self.assert_with_context(_assert1)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message1 = await transport2.receive(context)
            received_message2 = await transport2.receive(context)
            received_message3 = await transport2.receive(context)
            assert received_message1
            assert received_message2
            assert received_message1.headers.message_id == transport_message1.headers.message_id
            assert received_message2.headers.message_id == transport_message2.headers.message_id
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
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1, commit=False, ack=should_ack)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await transport2.receive(context)
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
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1, commit=True, ack=should_ack)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await transport2.receive(context)
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
        transport_message = TransportMessageBuilder.build()

        async def _assert1(context: DefaultTransactionContext) -> None:
            await transport1.send(transport2_address, transport_message, context)

        await self.assert_with_context(_assert1)

        async def _assert2(context: DefaultTransactionContext) -> None:
            received_message = await transport2.receive(context)
            assert received_message
            assert received_message.headers.message_id == transport_message.headers.message_id

        await self.assert_with_context(
            _assert2,
            commit=should_commit_first_time,
            ack=False,
            complete=should_complete,
        )

        async def _assert3(context: DefaultTransactionContext) -> None:
            received_message = await transport2.receive(context)
            assert received_message
            assert received_message.headers.message_id == transport_message.headers.message_id

        await self.assert_with_context(_assert3, commit=should_commit_second_time, ack=True)

        async def _assert4(context: DefaultTransactionContext) -> None:
            received_message = await transport2.receive(context)
            assert not received_message

        await self.assert_with_context(_assert4)
