import uuid
from typing import Any

import pytest

from mersal.messages import LogicalMessage, TransportMessage
from mersal.messages.message_headers import MessageHeaders
from mersal.pipeline import FlowCorrelationStep, IncomingStepContext
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.transport import DefaultTransactionContext
from mersal_testing.counter import Counter

__all__ = ("TestSetDefaultHeadersStep",)


pytestmark = pytest.mark.anyio


class TestSetDefaultHeadersStep:
    @pytest.mark.parametrize(
        "message_headers,expected_correlation_id,expected_correlation_sequence",
        [
            [
                {
                    MessageHeaders.message_id_key: "M1",
                },
                "M1",
                0,
            ],
            [
                {
                    MessageHeaders.message_id_key: uuid.uuid4(),
                    MessageHeaders.correlation_id_key: "M2 Foo",
                    MessageHeaders.correlation_sequence_key: 100,
                },
                "M2 Foo",
                100,
            ],
        ],
    )
    async def test_setting_correlation_data_when_outside_a_message_handler(
        self,
        message_headers: dict[str, Any],
        expected_correlation_id: Any,
        expected_correlation_sequence: int,
    ):
        subject = FlowCorrelationStep()
        message = LogicalMessage(
            body={},
            headers=MessageHeaders(
                message_headers,
            ),
        )

        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        counter = Counter()
        await subject(context, counter.task)

        assert message.headers.correlation_id == expected_correlation_id
        assert message.headers.correlation_sequence == expected_correlation_sequence
        assert counter.total == 1

    @pytest.mark.parametrize(
        "incoming_message_headers,expected_correlation_id,expected_correlation_sequence",
        [
            [
                {
                    MessageHeaders.message_id_key: "M1",
                },
                "M1",
                1,
            ],
            [
                {
                    MessageHeaders.message_id_key: uuid.uuid4(),
                    MessageHeaders.correlation_id_key: "M2 Foo",
                    MessageHeaders.correlation_sequence_key: 100,
                },
                "M2 Foo",
                101,
            ],
            [
                {
                    MessageHeaders.message_id_key: "M3",
                },
                "M3",
                1,
            ],
        ],
    )
    async def test_setting_correlation_data_when_inside_a_message_handler(
        self,
        incoming_message_headers: dict[str, Any],
        expected_correlation_id: Any,
        expected_correlation_sequence: int,
    ):
        transaction_context = DefaultTransactionContext()
        transport_message = TransportMessage(
            body=bytes("hi", "utf-8"),
            headers=MessageHeaders(
                incoming_message_headers,
            ),
        )
        _ = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )

        subject = FlowCorrelationStep()
        message = LogicalMessage(
            body={},
            headers=MessageHeaders(
                {MessageHeaders.message_id_key: uuid.uuid4()},
            ),
        )

        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        counter = Counter()
        await subject(context, counter.task)

        assert message.headers.correlation_id == expected_correlation_id
        assert message.headers.correlation_sequence == expected_correlation_sequence
        assert counter.total == 1
