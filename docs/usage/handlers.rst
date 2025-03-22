Message Handlers
===================


Overview
---------

When a message is :doc:`received <receiving>`, the configured incoming :doc:`pipeline <pipeline>` is activated. One of the steps run by the pipeline is executing all the message handlers.

Message handlers in Mersal are simply callables that define the message as the only parameter and it should process the message as required without returning anything. The callable should be asynchronous but support for synchronous handlers is tracked at `#23 <https://github.com/mersal-org/mersal/issues/23>`_ (please feel free to try it out, it might be actually working!)

Since handlers can be any callable, we are free to choose function or class based handlers (or do some ninja meta-programming moves that somehow generates a handler. As long is it can be called and accepts the message as an argument then it works!)

Function-based Handlers
^^^^^^^^^^^^^^^^^^^^^^

Here is a function based handler that handles a `SubmitOrderCommand` message.

.. code-block:: python

    from dataclasses import dataclass

    @dataclass
    class SubmitOrderCommand:
       order_id: str
       items: list[str]

    async def handle_order(order: SubmitOrderCommand) -> None:
        print(f"Processing order: {order.order_id}")
        # Process the order...

Class-based Handlers
^^^^^^^^^^^^^^^^^^^

The same handler can be defined as a class:

.. code-block:: python

    from dataclasses import dataclass

    @dataclass
    class SubmitOrderCommand:
       order_id: str
       items: list[str]

    class SubmitOrderCommandHandler:
        async def __call__(self, order: SubmitOrderCommand) -> None:
            print(f"Processing order: {order.order_id}")
            # Process the order...


Registering Message Handlers
--------------------------

So the incoming message pipeline executes the handlers as one of its many steps. How does it know which handlers to invoke? We must tell the Mersal app which handlers are associated with which message types. This is the purpose of :class:`HandlerActivator <.activation.HandlerActivator>`.

We use its :py:meth:`~.activation.HandlerActivator.register` method to associate message types with handlers. Mersal provides an implementation of a handler activator that should cover majority of use-cases via :class:`BuiltinHandlerActivator <.activation.BuiltinHandlerActivator>`.

Notice that the method for registration takes a sync callable as the second argument. This is **not** our message handler but a factory that should generate the handler (hence why it's named `factory` of type `HandlerFactory`). Lets forget about that part for a moment and see an example of registering message handlers.

.. note::

   The type of `HandlerFactory` is

    .. code-block:: python

        HandlerFactory: TypeAlias = Callable[
            [MessageContext, "Mersal"],
            MessageHandler[MessageT],
        ]

    until issue `#24 <https://github.com/mersal-org/mersal/issues/24>`_ is resolved.

.. code-block:: python

    from dataclasses import dataclass

    from mersal.app import Mersal
    from mersal.activation import BuiltinHandlerActivator

    @dataclass
    class SubmitOrderCommand:
       order_id: str
       items: list[str]

    class SubmitOrderCommandHandler:
        async def __call__(self, order: SubmitOrderCommand) -> None:
            print(f"Processing order: {order.order_id}")
            # Process the order...

    # Define a handler factory function
    def submit_order_command_handler_factory(_, __):
        return SubmitOrderCommandHandler()

    # Create activator and register the handler
    activator = BuiltinHandlerActivator()
    activator.register(SubmitOrderCommand, submit_order_command_handler_factory)

    # Create the Mersal application passing in the activator and other args.
    app = Mersal("orders-service",
                activator,
                #...
            )

The message handler factory doesn't need to be defined as a named function. We could have used a `lambda` just fine:

.. code-block:: python

    activator.register(SubmitOrderCommand, lambda _, __: SubmitOrderCommandHandler())

Multiple Handlers for the Same Message Type
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can register multiple handlers for the same message type, and all handlers will be invoked when a message of that type is received:

.. code-block:: python

    # Register multiple handlers for the same message type
    activator.register(SubmitOrderCommand, lambda _, __: SubmitOrderCommandProcessingHandler())
    activator.register(SubmitOrderCommand, lambda _, __: SubmitOrderCommandAuditingHandler())
    activator.register(SubmitOrderCommand, lambda _, __: SubmitOrderCommandNotificationHandler())

The invocations are guaranteed to follow the order of registration (but perhaps it isn't a wise decision to rely on such guarantee from a business perspective.)

Same Handler for Multiple Message Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Just like the fact that messages can be handled by multiple handlers. A single handler can process multiple type of messages.

.. code-block:: python

    # Register the same handler type for different messages
    activator.register(SubmitOrderCommand, lambda _, __: SubmitAndRejectOrderCommandHandler())
    activator.register(RejectOrderCommand, lambda _, __: SubmitAndRejectOrderCommandHandler())

Handlers with Message Context and Mersal app instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Handlers can access both the :doc:`message context <message_context>` and the :doc:`Mersal app <app>` instance. The first allow the handler to obtain information about the message (see relevant docs) and the other allows for invoking Mersal app functionalities inside the message handler (e.g. send/publish a message.)

The message context and Mersal app instance are the parameters we skipped earlier that are part of the handler factory.

Here is how to use this with a class based handler:

.. code-block:: python

    class SubmitOrderCommandHandler:
        def __init__(self, message_context: MessageContext, app: Mersal):
            self.message_context = message_context
            self.app = app

        async def __call__(self, order: SubmitOrderCommand) -> None:
            # Access message headers
            correlation_id = self.message_context.headers.get("correlation_id")
            print(f"Processing order {order.order_id} with correlation ID: {correlation_id}")

            # Process the order...
            await self.app.publish(...)

    activator = BuiltinHandlerActivator()
    activator.register(SubmitOrderCommand, lambda message_context, mersal_app: SubmitOrderCommandHandler(message_context, mersal_app))

And here is the same approach with a function based handler:

.. code-block:: python

    class SubmitOrderCommandHandler:
        def __init__(self, message_context: MessageContext, app: Mersal):
            self.message_context = message_context
            self.app = app

    def handle_order_factory(message_context: MessageContext, mersal_app: Mersal):
        async def handle_order(order: SubmitOrderCommand) -> None:
            # Access message headers
            correlation_id = message_context.headers.get("correlation_id")
            print(f"Processing order {order.order_id} with correlation ID: {correlation_id}")

            # Process the order...
            await app.publish(...)

        return handle_order

    activator = BuiltinHandlerActivator()
    activator.register(SubmitOrderCommand,
    lambda message_context, mersal_app: handle_order_factory(message_context, mersal_app))

For the above example a more Pythonic code would be:

.. code-block:: python

    activator.register(SubmitOrderCommand, handle_order_factory)
