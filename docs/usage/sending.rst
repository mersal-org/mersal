Sending Messages
==================

Overview
----------

So now we have setup our Mersal app with our chosen transport. It's time to send and receive messages. This sections covers sending while the next discusses receiving.

It's important to note here that in message driven systems, sending and receiving are completely separate processes [#]_. It's a one way communication system. We can even have a Mersal app that only sends messages but doesn't handle any messages - see :ref:`send-only apps <send_only_apps>`.

.. note::
    You can send messages without :ref:`starting <starting_app>` the Mersal application. This might be useful in environments where startup time is important, for example in serverless offerings.

Sending is typically initiated by some form of input. For example in a web application we send a message upon receiving a `POST` request to our defined endpoint.

In message driven systems, a message is usually sent to a single address. These are usually named **commands**. Message that are sent to multiple addresses are said to be :doc:`**published** <pub_sub>` and they are usually called **events**.

While Mersal doesn't enforce any naming standard for messages, it does enforce the idea of `send` vs `publish`. Lets see how to send to an address.


Sending Local Messages
------------------------

When we setup a Mersal app with a transport, we configure the transport with a specific address. In most situations we will be using Mersal to send messages to its own configured transport. We call this local sending. It is invoked via the :py:meth:`mersal.core.app.Mersal.send_local` method:

.. code-block:: python

    from mersal.core.app import Mersal
    from mersal.activation import BuiltinHandlerActivator
    from mersal.transport.in_memory import InMemoryNetwork
    from mersal.transport.in_memory.in_memory_transport_plugin import InMemoryTransportPluginConfig

    class MyMessage:
        def __init__(self, content):
            self.content = content

    network = InMemoryNetwork()
    queue_address = "my-queue"
    activator = BuiltinHandlerActivator()
    plugins = [InMemoryTransportPluginConfig(network, queue_address).plugin]
    app = Mersal("my-app", activator, plugins=plugins)

    message = MyMessage("Hello, Mersal!")
    # This will send a message using the configured transport and it will use
    # "my-queue" as the address
    await app.send_local(message)


Sending to an Arbitrary Destination
-------------------------------------

To send a message to an arbitrary destination, we need to first setup :doc:`routing <routing>` in order for Mersal to know the destination address. Once that is set, we use the :py:meth:`mersal.core.app.Mersal.send` method:

.. code-block:: python

    from mersal.core.app import Mersal
    from mersal.activation import BuiltinHandlerActivator
    from mersal.transport.in_memory import InMemoryNetwork
    from mersal.transport.in_memory.in_memory_transport_plugin import InMemoryTransportPluginConfig
    from mersal.routing.default import DefaultRouterRegistrationConfig

    router_config = DefaultRouterRegistrationConfig({
        "orders-queue": [SubmitOrderCommand, CancelOrderCommand],
        "inventory-queue": [UpdateInventoryCommand],
        "shipping-queue": [ShipOrderCommand]
    })

    # Use the router configuration when creating the app
    plugins = [
        InMemoryTransportPluginConfig(network, "my-app-queue").plugin,
        router_config.plugin
    ]
    app = Mersal("my-app", activator, plugins=plugins)

    class SubmitOrderCommand:
        def __init__(self, order_id, items):
            self.order_id = order_id
            self.items = items

    order = SubmitOrderCommand("12345", ["item1", "item2"])
    # internally the router will determine which address to send to
    await app.send(order)


See :doc:`routing` for more details on how to configure message routing.

Adding Message Headers
------------------------

Both ``send`` and ``send_local`` methods accept an optional ``headers`` parameter that allows you to include additional metadata with your message.

.. code-block:: python

    # Send a message with custom headers
    headers = {
        "correlation_id": "12345",
        "user_id": "user-abc",
        "priority": "high"
    }
    await app.send(message, headers)

Headers are useful for including metadata like correlation IDs, authentication information, or any other contextual data that might be needed by message handlers.

By default, Mersal adds specific headers to the message if they don't exist. See :ref:`automatic headers <automatic_headers>`

Deferring Messages
--------------------

A message can be scheduled for delivery in the future with :py:meth:`mersal.core.app.Mersal.defer` and :py:meth:`mersal.core.app.Mersal.defer_local`. They mirror ``send`` and ``send_local`` but take a delay first:

.. code-block:: python

    from datetime import timedelta

    # delivered to this app's own address in 10 minutes
    await app.defer_local(timedelta(minutes=10), ReminderCommand("12345"))

    # delivered to the routed owner of the message in an hour
    await app.defer(timedelta(hours=1), CancelOrderCommand("12345"))

The message gets two headers:

- ``deferred_until``: the ISO 8601 (UTC) time before which the message must not be handled.
- ``deferred_recipient``: the address the message is delivered to once due. Passing this header explicitly overrides the destination.

How the message is held back depends on the transport:

1. **Native deferral**: if the transport can delay delivery itself (:py:attr:`~mersal.transport.Transport.supports_deferral`, e.g. RabbitMQ with the delayed message exchange), the message is sent to its recipient directly and the transport delays it.
2. **Timeout manager**: otherwise, the message is sent to a timeout manager, which stores it and sends it to its recipient once due. Configure one with :py:class:`~mersal.timeouts.TimeoutsConfig`.

Without either, deferring raises :py:class:`~mersal.exceptions.DeferralNotSupportedError`.

Either way, the delivered message no longer carries the defer headers.

Timeout manager
^^^^^^^^^^^^^^^^

An app becomes a timeout manager by giving it a storage for deferred messages:

.. code-block:: python

    from mersal.persistence.in_memory import InMemoryTimeoutManager
    from mersal.timeouts import TimeoutsConfig

    app = Mersal(
        "my-app",
        activator,
        plugins=plugins,
        timeouts=TimeoutsConfig(storage=InMemoryTimeoutManager()),
    )

Deferred messages are then sent to the app's own address. When the app receives one, it stores it instead of handling it, and checks the storage every ``poll_interval`` seconds (default ``1``) for messages that are due.

.. warning::
    :py:class:`~mersal.persistence.in_memory.InMemoryTimeoutManager` loses deferred messages when the process stops. Use a durable storage in production, e.g. ``SQLAlchemyTimeoutManager`` from ``mersal-sqlalchemy``:

    .. code-block:: python

        from mersal.sqlalchemy import SQLAlchemyTimeoutManagerConfig

        storage = SQLAlchemyTimeoutManagerConfig(
            async_session_factory=async_sessionmaker(engine, expire_on_commit=False),
            table_name="mersal_timeouts",
        ).storage
        app = Mersal(..., timeouts=TimeoutsConfig(storage=storage))

    It fetches due messages with ``SELECT ... FOR UPDATE SKIP LOCKED``, so several instances of the timeout manager app can share the table without sending a message twice.

Instead of every app storing its own deferred messages, one app can be the timeout manager for others, which point to it:

.. code-block:: python

    # the app hosting the timeout manager
    timeouts_app = Mersal(..., timeouts=TimeoutsConfig(storage=storage))

    # other apps, including send-only ones
    app = Mersal(..., timeouts=TimeoutsConfig(external_timeout_manager_address="timeouts"))

A send-only app can't host a timeout manager since it never receives, so it must use an external one.

An app that receives a deferred message without a timeout manager configured fails the message (it ends up in the error queue) rather than handling it early.

Transactions
---------------

Mersal wraps the sending (and receiving) process in a transaction to ensure that messages are processed reliably (think something like a DB transaction).

When you send a message outside a message handler, Mersal automatically creates a transaction context if one doesn't already exist. The message will be sent when the transaction is committed. This is the simple case, any custom step can cause the transaction to be rolledback/cancelled. Non of the default outgoing steps cause transaction cancellation or rollbacks.

When sending a message from inside a message handler, it's a different case since there will be a transaction already started by the incoming message pipeline. This will be discussed in the :doc:`receiving <receiving>` section.

For more details on transactions and how they ensure reliable message processing, see :doc:`transactions`.

Summary
---------

Sending messages in Mersal is straightforward:

1. Use ``send_local`` to send messages to the address defined within the same application.
2. Use ``send`` to send messages to destinations based on routing.
3. Use ``defer`` / ``defer_local`` to schedule a message for later delivery.
4. Add custom headers to include metadata with your messages.

Next, we'll explore how to receive and process these messages.

.. [#] Request/Reply pattern in message driven system allows for two way communication. Mersal doesn't support this pattern directly, this is tracked in `#25 <https://github.com/mersal-org/mersal/issues/25>`_. However, :doc:`polling <contrib/polling>` already provides a way to "wait" for a certain response.
