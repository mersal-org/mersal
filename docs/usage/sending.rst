Sending Messages
===============

..
   Overview
   --------

   In Mersal, sending messages is a fundamental operation that allows services to communicate with each other. Mersal provides flexible ways to send messages to different destinations.

   Key Features:

   * Send messages to local or remote destinations
   * Automatic message routing based on message type
   * Transaction support for reliable message delivery
   * Custom message headers for metadata

   Sending Local Messages
   ---------------------

   The simplest form of sending messages is to send them locally within the same application. This is useful for testing or when you want to process a message within the same application instance.

   .. code-block:: python

       from mersal.app import Mersal
       from mersal.activation import BuiltinHandlerActivator
       from mersal.transport.in_memory import InMemoryNetwork
       from mersal.transport.in_memory.in_memory_transport_plugin import InMemoryTransportPluginConfig

       # Define a simple message class
       class MyMessage:
           def __init__(self, content):
               self.content = content

       # Create a Mersal application
       network = InMemoryNetwork()
       queue_address = "my-queue"
       activator = BuiltinHandlerActivator()
       plugins = [InMemoryTransportPluginConfig(network, queue_address).plugin]
       app = Mersal("my-app", activator, plugins=plugins)

       # Create and send a message locally
       message = MyMessage("Hello, Mersal!")
       await app.send_local(message)

   When using ``send_local``, the message is sent to the application's own transport address, making it available for local processing by the application's message handlers.

   .. note::
      You can send messages without starting the Mersal application, which is particularly useful in web applications.

   Sending to Remote Destinations
   -----------------------------

   To send a message to a remote destination, use the ``send`` method:

   .. code-block:: python

       from mersal.app import Mersal
       from mersal.activation import BuiltinHandlerActivator
       from mersal.routing.default import DefaultRouterRegistrationConfig

       # Define message classes
       class OrderCommand:
           def __init__(self, order_id, items):
               self.order_id = order_id
               self.items = items

       # Create and send a message to the remote destination
       order = OrderCommand("12345", ["item1", "item2"])
       await app.send(order)

   When using ``send``, Mersal needs to determine the destination address for the message. This is handled by the :ref:`routing` system, which maps message types to destination addresses.

   See :doc:`routing` for more details on how to configure message routing.

   Adding Message Headers
   ---------------------

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

   Transactions
   -----------

   Mersal uses a transaction context to ensure that messages are processed reliably. When you send a message, Mersal automatically creates a transaction context if one doesn't already exist.

   .. code-block:: python

       from mersal.transport import DefaultTransactionContextWithOwningApp

       # Using an explicit transaction context
       async with DefaultTransactionContextWithOwningApp(app) as transaction_context:
           await app.send(message)
           # Other operations within the same transaction...

   For more details on transactions and how they ensure reliable message processing, see :doc:`transactions`.

   Summary
   -------

   Sending messages in Mersal is straightforward:

   1. Use ``send_local`` to send messages within the same application
   2. Use ``send`` to send messages to remote destinations based on routing
   3. Add custom headers to include metadata with your messages
   4. Take advantage of transaction contexts for reliable message delivery

   Next, we'll explore how to receive and process these messages using Mersal's message handling system.
