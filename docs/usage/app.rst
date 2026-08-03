Mersal App
============


Starting
------------

.. _starting_app:


Autosubscribe
----------------

Passing a :py:class:`mersal.lifespan.autosubscribe.AutosubscribeConfig` to the ``autosubscribe`` argument allows for subscribing to passed events on startup. See :ref:`pub/sub <pub_sub_autosubscribe>`

.. _send_only_apps:

Send-only Apps
------------------

Some apps only need to :doc:`send or publish <sending>` messages and never receive any - for example a web app that only submits commands, or a script that only publishes events. Pass ``send_only=True`` when constructing :py:class:`mersal.app.Mersal` to mark an app as :term:`send-only`:

.. code-block:: python

    app = Mersal(
        "my-app",
        activator,
        plugins=plugins,
        send_only=True,
    )

A send-only app never creates a :doc:`worker <workers>`, so it will never poll the transport for incoming messages - calling ``start`` still runs startup lifespan hooks (so the transport still connects), it just skips starting the worker.

Transport implementations can read the ``send_only`` flag off the ``StandardConfigurator`` passed to their plugin, and use it to decide whether to set up resources that are only needed for receiving (e.g. an input queue, subscription, or consumer):

.. code-block:: python

    class MyTransportPlugin:
        def __call__(self, configurator: StandardConfigurator) -> None:
            def register_transport(configurator: StandardConfigurator) -> MyTransport:
                return MyTransport(send_only=configurator.send_only, ...)

            configurator.register(Transport, register_transport)

Both the ``mersal_rabbitmq`` and ``mersal_gcp_pubsub`` transports already honor this: when ``send_only`` is set, they skip declaring/binding their own input queue and never start a consumer for it.
