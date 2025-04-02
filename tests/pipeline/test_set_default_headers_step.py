import uuid

import pytest

from mersal.messages import LogicalMessage
from mersal.messages.message_headers import MessageHeaders
from mersal.pipeline import SetDefaultHeadersStep
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.transport import DefaultTransactionContext
from mersal_testing.counter import Counter

__all__ = ("TestSetDefaultHeadersStep",)


pytestmark = pytest.mark.anyio


class TestSetDefaultHeadersStep:
    async def test_setting_default_headers_and_calling_next_step(self):
        subject = SetDefaultHeadersStep()
        message = LogicalMessage(body={}, headers=MessageHeaders())

        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        counter = Counter()
        await subject(context, counter.task)

        assert message.headers.get("message_id")
        assert counter.total == 1

    async def test_not_setting_default_headers_if_they_exist_and_calling_next_step(
        self,
    ):
        subject = SetDefaultHeadersStep()
        message_id = uuid.uuid4()
        message = LogicalMessage(body={}, headers=MessageHeaders({"message_id": message_id}))

        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        counter = Counter()
        await subject(context, counter.task)

        assert message.headers.get("message_id") == message_id
        assert counter.total == 1

    async def test_using_a_custom_message_id_generator(self):
        subject = SetDefaultHeadersStep(message_id_generator=lambda message: "message_1")
        message = LogicalMessage(body={}, headers=MessageHeaders())

        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        counter = Counter()
        await subject(context, counter.task)

        assert message.headers.get("message_id") == "message_1"
        assert counter.total == 1
