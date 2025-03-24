Receiving Messages
====================

Overview
-----------

With the Mersal app setup and :ref:`started <starting_app>`, and message handlers are registered. Any messages sent to the transport with our configured address will be fetched and processed using the registered handlers.

What can send a message to the transport?
-------------------------------------------

While we can use a Mersal app to :doc:`send <sending>` a message via the transport to any address we desire. That's not the only way!

Another system written in a completely different language could have sent the message. It could have been a 3rd party application.

This is the power of message driven systems. It allows for loose coupling between systems where they only share a "post office" that exchanges messages between them.

How are messages received?
----------------------------

The actual component that is responsible for receiving messages is the Mersal :doc:`worker <workers>`. This is why we need to start the Mersal app since internally that starts the workers among other things.

The current available worker polls the transport for new messages (so it's a pull based mechanism). This aligns well with the way most transports work (pull based). Support for push based transports (e.g GCP Pub/Sub in push mode) is tracked in `#26 <https://github.com/mersal-org/mersal/issues/26>`_.

Once the transport has a message, the worker will pull it and the incoming :doc:`pipeline <pipeline>` is activated to process the message.


Processing Flow
-----------------

The following describes roughly what the default incoming message pipeline does:

1. The whole processing is wrapped with error handling
2. The message is deserialized if necessary
3. Appropriate handlers are activated based on the message type
4. After all handlers complete, the message is acknowledged


For more details on the message processing pipeline, see :doc:`pipeline`.

Error Handling
-----------------

By default, if a handler raises an exception, the message processing is considered failed. Mersal provides several error handling strategies, including retries and dead-letter queues.

See :doc:`error_handling` for more details on how to handle failures in message processing.

Transaction Handling
----------------------

Mersal wraps the receiving (and sending) process in a transaction to ensure that messages are processed reliably (think something like a DB transaction).

The transaction can be either committed or rolledback. It can also be acknowledged (ack) or negative acknowledged (nack).

For the transport, acknowledging the transaction means we are telling the transport that we have completed processing this message and it can be removed from the queue. Negative acknowledgement means the transport will keep the message in the queue (depending on the transport implementation, the message might be moved to the back of the queue). Different transports will behave differently to ack and nack responses. This should be documented by each transport.

The transaction is acknowledged upon either successful processing or if the message has failed too many times and has been moved to the dead letter queue (see error handling).

Sending a message within a message handler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As discussed previously, message handlers can :ref:`obtain <handlers_with_app>` the Mersal app instance in order to use it within the handler to publish/send messages.

Because there is an ongoing transaction (started by receiving process), the sent/published messages are only sent when the transaction is committed. The transaction is only committed when the message handling is completed successfully.

The following two examples are identical since the event is only published if the processing is completed without any errors.

.. code-block:: python

    class SubmitOrderCommandHandler:
        def __init__(self, message_context: MessageContext, app: Mersal):
            self.message_context = message_context
            self.app = app

        async def __call__(self, order: SubmitOrderCommand) -> None:

            # await process order

            # Processed the order...
            await self.app.publish(OrderProcessedEvent(order_id: order.order_id))

.. code-block:: python

    class SubmitOrderCommandHandler:
        def __init__(self, message_context: MessageContext, app: Mersal):
            self.message_context = message_context
            self.app = app

        async def __call__(self, order: SubmitOrderCommand) -> None:

            # Processed the order...
            await self.app.publish(OrderProcessedEvent(order_id: order.order_id))

            # await process order

It doesn't make a difference when we publish/send messages within a handler, it only happens after successful processing.

If multiple messages are sent within a handler, they will be sent in the correct order.

.. note::

   But what happens if the message is processed successfully but the outgoing message fails to be sent, this will break business consistency!

   This issue is solved with the :doc:`outbox <outbox>` pattern.

For more details on transaction handling, see :doc:`transactions`.
