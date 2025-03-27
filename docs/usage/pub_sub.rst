Pub/Sub
============


Overview
-----------

Pub/Sub is a common pattern (if not the most common) in message driven architecture. One or multiple services/apps/systems **subscribe** to a certain topic (sometimes called "channel)" and whenever a message is **published** to that channel/topic the apps will receive them in order to process them.

Pub/Sub can be thought of a more generic function of sending. When :doc:`sending <sending>` was discussed, it was mentioned that "commands" are sent to a certain destination. In pub/sub, "events" are sent (published) to any listener (subscriber).

First lets see how to subscribe and publish then the configuration of pub/sub will be discussed.

Subscription
----------------

With a Mersal app, we can subscribe to any message using the :py:meth:`mersal.app.Mersal.subscribe` method. Subscribing to messages is usually something done unconditionally when we setup the app. However, the subscription can be made at any other time.

.. code-block:: python

    from dataclasses import dataclass

    from mersal.app import Mersal

    @dataclass
    class OrderProcessedEvent:
        order_id: str

    class OrderProcessedEventHandler:
        async def __call__(self, event: OrderProcessedEvent) -> None:
            pass

    def order_processed_event_handler_factory(_, __):
        return OrderProcessedEventHandler()

    activator = BuiltinHandlerActivator()
    activator.register(OrderProcessedEvent, order_processed_event_handler_factory)
    app = Mersal("my-app",
        activator,
        #...
    )

    await app.subscribe(OrderProcssedEvent)

Autosubscribe
^^^^^^^^^^^^^^^^

.. _pub_sub_autosubscribe:

Since messages are usually subscribed to on app startup, Mersal provides a shortcut to do this.

The following example is equivalent to the one above, it saves some lines of code if multiple messages need to be subscribed to. There is one gotcha with using autosubscribe, the Mersal app needs to be started, the actual auto-subscription is invoked upon startup rather than initialization (tracked in `#27 <https://github.com/mersal-org/mersal/issues/27>`_)

.. code-block:: python

    from dataclasses import dataclass
    from mersal.lifespan.autosubscribe import AutosubscribeConfig
    from mersal.app import Mersal

    @dataclass
    class OrderProcessedEvent:
        order_id: str

    class OrderProcessedEventHandler:
        async def __call__(self, event: OrderProcessedEvent) -> None:
            pass

    def order_processed_event_handler_factory(_, __):
        return OrderProcessedEventHandler()

    activator = BuiltinHandlerActivator()
    activator.register(OrderProcessedEvent, order_processed_event_handler_factory)
    app = Mersal("my-app",
        activator,
        #...
        autosubscribe=AutosubscribeConfig(events={OrderProcessedEvent,})
    )
    # we need this for autosubscribe
    await app.start()

The above is a short cut for using the autosubscribe plugin. The plugin can be used directly like any other :doc:`plugin <plugins>` in Mersal.

.. code-block:: python

    from dataclasses import dataclass
    from mersal.lifespan.autosubscribe.autosubscribe_plugin import AutosubscribePlugin, AutosubscribeConfig
    from mersal.app import Mersal

    @dataclass
    class OrderProcessedEvent:
        order_id: str

    class OrderProcessedEventHandler:
        async def __call__(self, event: OrderProcessedEvent) -> None:
            pass

    def order_processed_event_handler_factory(_, __):
        return OrderProcessedEventHandler()

    activator = BuiltinHandlerActivator()
    activator.register(OrderProcessedEvent, order_processed_event_handler_factory)

    autosubscribe_plugin = AutosubscribePlugin(
                AutosubscribeConfig(events={OrderProcessedEvent,})
    )
    app = Mersal("my-app",
        activator,
        #...
        plugins=[autosubscribe_plugin]
    )
    await app.start()

Publishing
----------------

With a Mersal app, we can publish any message using the :py:meth:`mersal.app.Mersal.publish` method. Just like sending, we can attach optional headers to the published message.

Unsubscribing
----------------

Currently not supported. `#29 <https://github.com/mersal-org/mersal/issues/29>`_

Topic names
----------------

By default, Mersal uses dunder name ``__name__`` of the subscribed message to determine the name of the topic.

This can be customised by passing an appropriate implementation of :py:class:`mersal.topic.TopicNameConvention` to the ``topic_name_convention`` argument of Mersal app.

Configuring Pub/Sub
-----------------------

When we discussed sending, we noted that a :doc:`router <routing>` is needed to send messages. The router determines the destination address.

In pub/sub, we need a component that helps us store which apps are subscribed to which topics. This is why we need to provide Mersal with an instance of :py:class:`mersal.subscription.SubscriptionStorage`. This is either provided via the ``subscription_storage`` argument passed to the :py:class:`mersal.app.Mersal` app or via a plugin. Pub/sub will **not** work without providing this.

Most message brokers support pub/sub natively (e.g. RabbitMQ, GCP Pub/Sub), so a Mersal transport implementation for those brokers will have an appropriate implementation for a ``SubscriptionStorage``.

If the broker doesn't support pub/sub (e.g. using a database as a Mersal transport), then we have to implement a suitable ``SubscriptionStorage``. Mersal core provides an :py:class:`mersal.persistence.in_memory.InMemorySubscriptionStorage` that can be used to store subscriptions in memory.

.. code-block:: python

    from dataclasses import dataclass
    from mersal.persistence.in_memory import (
        InMemorySubscriptionStorage,
        InMemorySubscriptionStore,
    )
    from mersal.app import Mersal

    subscription_store = InMemorySubscriptionStore()
    app = Mersal("my-app",
        activator,
        subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
    )

.. note::

   "Centralized" means all subscriptions are stored in a single location and a call to :py:meth:`mersal.app.Mersal.subscribe` will immediately invoke the registration of a subscription to the given topic. Non Centralized means the subscription and unsubscription is performed by sending messages. Issue `#28 <https://github.com/mersal-org/mersal/issues/28>`_ discusses if this is needed or not.

   Currently non-centralized isn't supported until a transport that has native pub/sub is implemented.
