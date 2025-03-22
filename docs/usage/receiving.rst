Receiving Messages
=================

..
   Overview
   --------

   Receiving and processing messages is a core functionality of Mersal. Messages are received by configuring handlers to process specific message types.

   Key Features:

   * Register handlers for specific message types
   * Support for multiple handlers per message type
   * Automatic message deserialization
   * Access to message headers and context

   Defining Message Handlers
   ------------------------



   Starting the Application to Receive Messages
   ------------------------------------------

   To start processing messages, you need to start the Mersal application:

   .. code-block:: python

       # Start the application and process messages
       await app.start()

       # ... application runs and processes messages ...

       # Stop the application when done
       await app.stop()

   Using the Context Manager
   ^^^^^^^^^^^^^^^^^^^^^^^^

   Alternatively, you can use the application as an async context manager:

   .. code-block:: python

       async with app:
           # Application is started and processing messages
           # Wait for some condition or simply sleep
           await asyncio.sleep(60)  # Run for 60 seconds
       # Application is automatically stopped when exiting the context

   Processing Flow
   -------------

   When a message is received:

   1. The transport receives the message from the underlying message broker or in-memory queue
   2. The message is deserialized if necessary
   3. Appropriate handlers are activated based on the message type
   4. Each handler is invoked with the message
   5. After all handlers complete, the message is acknowledged

   For more details on the message processing pipeline, see :doc:`pipeline`.

   Error Handling
   ------------

   By default, if a handler raises an exception, the message processing is considered failed. Mersal provides several error handling strategies, including retries and dead-letter queues.

   See :doc:`error_handling` for more details on how to handle failures in message processing.

   Transaction Handling
   ------------------

   Messages are processed within a transaction context that coordinates acknowledgment and commits. This ensures that messages are only acknowledged when all handlers have successfully processed them.

   For more details on transaction handling, see :doc:`transactions`.

   Summary
   -------

   Receiving messages in Mersal involves:

   1. Defining message handlers (functions or classes)
   2. Registering handlers with a handler activator
   3. Creating and starting a Mersal application
   4. Letting the application process messages automatically

   The message processing system is designed to be extensible and configurable, allowing you to adapt it to different messaging patterns and requirements.
