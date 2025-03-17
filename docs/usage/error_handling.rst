Error Handling
=================

Introduction
-------------

Handling errors in message-based systems is crucial for building robust applications. Mersal provides a comprehensive error handling system with features for:

1. Tracking and managing errors
2. Implementing retry strategies
3. Identifying messages that should fail immediately (fail-fast)
4. Handling poisonous messages via dead letter queues

These features help ensure that your application can gracefully handle failures, improve reliability, and avoid getting stuck in endless retry loops.

Usage
-------

Notes
^^^^^^

Default Error Handling
"""""""""""""""""""""""

Mersal comes with a default error handling strategy that provides these key capabilities:

- **Error Tracking**: Records errors for each message and tracks how many times it has failed
- **Retry Logic**: Automatically retries failed messages up to a configurable number of times
- **Fail-Fast Detection**: Identifies exceptions that should immediately fail without retries
- **Dead Letter Queue**: Forwards messages that fail repeatedly to a dedicated error queue

The default retry strategy is implemented in the ``DefaultRetryStrategy`` class, which creates a ``DefaultRetryStep`` in the message processing pipeline.

Customizing Error Handling
"""""""""""""""""""""""""""

You can customize the error handling mechanism by configuring these components:

1. **Error Tracker**: Tracks errors for messages and determines when they've failed too many times
2. **Error Handler**: Handles poisonous messages, typically by sending them to a dead letter queue
3. **Fail-Fast Checker**: Determines which exceptions should cause immediate failure without retries

Here's an example of configuring error handling when creating a Mersal application:

.. code-block:: python

    from mersal.app import Mersal
    from mersal.retry.error_tracking.in_memory_error_tracker import InMemoryErrorTracker
    from mersal.retry.error_handling.deadletter_queue_error_handler import DeadletterQueueErrorHandler
    from mersal.retry.fail_fast.default_fail_fast_checker import DefaultFailFastChecker
    from mersal.retry.default_retry_strategy import DefaultRetryStrategy
    from mersal.retry.retry_strategy_settings import RetryStrategySettings

    # Configure error handling components
    error_tracker = InMemoryErrorTracker(maximum_failure_times=5)

    # Define exceptions that should fail immediately
    fail_fast_exceptions = [ValueError, KeyError]
    fail_fast_checker = DefaultFailFastChecker(fail_fast_exceptions)

    # Create the app with custom error handling
    app = Mersal(
        # Other configuration...
        retry_strategy=DefaultRetryStrategy(
            error_tracker=error_tracker,
            error_handler=DeadletterQueueErrorHandler(transport, "error_queue"),
            fail_fast_checker=fail_fast_checker,
        ),
        retry_strategy_settings=RetryStrategySettings(
            error_queue_name="error_queue",
            max_no_of_retries=5
        )
    )

Error Tracking
""""""""""""""

The error tracker component maintains the state of errors for each message:

- Records exceptions that occur during message processing
- Determines when a message has failed too many times
- Supports marking messages as "final" to skip retries
- Provides access to previous exceptions for diagnostics

Mersal includes an in-memory implementation (`InMemoryErrorTracker`), but you can implement the `ErrorTracker` protocol to create a persistent tracker using a database.

.. code-block:: python

    from mersal.retry.error_tracking.error_tracker import ErrorTracker
    import uuid

    class CustomErrorTracker(ErrorTracker):
        async def register_error(self, message_id: uuid.UUID, exception: Exception):
            # Record the error in your persistence store
            ...

        async def clean_up(self, message_id: uuid.UUID):
            # Remove error tracking for this message
            ...

        async def has_failed_too_many_times(self, message_id: uuid.UUID) -> bool:
            # Determine if message has exceeded retry limit
            ...

        async def mark_as_final(self, message_id: uuid.UUID):
            # Mark message as final (no more retries)
            ...

        async def get_exceptions(self, message_id: uuid.UUID) -> list[Exception]:
            # Return all exceptions for this message
            ...

Fail-Fast Strategies
""""""""""""""""""""

Not all errors should be retried. Some exceptions indicate that retrying will never succeed, such as:

- Validation errors
- Authorization failures
- Malformed message content

The fail-fast checker determines which exceptions should cause immediate failure:

.. code-block:: python

    from mersal.retry.fail_fast.default_fail_fast_checker import DefaultFailFastChecker

    # Define exceptions that should never be retried
    fail_fast_exceptions = [
        ValueError,  # Message validation issues
        PermissionError,  # Authorization failures
        KeyError,  # Missing required data
        TypeError  # Type conversion errors
    ]

    fail_fast_checker = DefaultFailFastChecker(fail_fast_exceptions)

Dead Letter Queue Handling
""""""""""""""""""""""""""

When a message fails repeatedly, it's sent to a dead letter queue for later investigation. This prevents the system from getting stuck in endless retry loops.

The default implementation (`DeadletterQueueErrorHandler`) sends failed messages to a configured error queue:

.. code-block:: python

    from mersal.retry.error_handling.deadletter_queue_error_handler import DeadletterQueueErrorHandler

    # Create error handler that sends to "error_queue"
    error_handler = DeadletterQueueErrorHandler(
        transport,
        error_queue_name="error_queue"
    )

The error handler adds the exception details to the message headers before forwarding it, making it easier to diagnose issues.

Examples
^^^^^^^^^

.. dropdown:: Complete Error Handling Configuration

   .. code-block:: python
      :linenos:
      :emphasize-lines: 25-28,37-42,51-55

      from mersal.app import Mersal
      from mersal.retry.error_tracking.in_memory_error_tracker import InMemoryErrorTracker
      from mersal.retry.error_handling.deadletter_queue_error_handler import DeadletterQueueErrorHandler
      from mersal.retry.fail_fast.default_fail_fast_checker import DefaultFailFastChecker
      from mersal.retry.default_retry_strategy import DefaultRetryStrategy
      from mersal.retry.retry_strategy_settings import RetryStrategySettings
      from mersal.transport.in_memory import InMemoryTransport

      # Define message and handler
      class MyMessage:
          def __init__(self, value: str):
              self.value = value

      class MyHandler:
          def __init__(self):
              self.processed = []
              self.failed = []

          async def __call__(self, message: MyMessage):
              if message.value == "fail":
                  raise ValueError("Message processing failed")
              self.processed.append(message)

      # Configure error handling
      transport = InMemoryTransport()

      # Configure which exceptions should fail immediately without retries
      fail_fast_exceptions = [KeyError, TypeError]
      fail_fast_checker = DefaultFailFastChecker(fail_fast_exceptions)

      # Track errors for up to 3 attempts
      error_tracker = InMemoryErrorTracker(maximum_failure_times=3)

      # Create app with custom retry strategy
      app = Mersal(
          transport=transport,
          # Configure error handling components
          retry_strategy=DefaultRetryStrategy(
              error_tracker=error_tracker,
              error_handler=DeadletterQueueErrorHandler(transport, "error_queue"),
              fail_fast_checker=fail_fast_checker,
          ),
          retry_strategy_settings=RetryStrategySettings(
              error_queue_name="error_queue",
              max_no_of_retries=3
          )
      )

      # Register message handler
      handler = MyHandler()
      app.register_handler(MyMessage, handler)

      # Process error queue messages
      error_handler = MyHandler()
      app.subscribe("error_queue", MyMessage, error_handler)

      # Main processing loop
      async def process_messages():
          # This will be retried up to 3 times
          await app.send("myqueue", MyMessage("normal"))

          # This will fail and go to error queue
          await app.send("myqueue", MyMessage("fail"))

          # This will fail fast without retries
          try:
              await app.send("myqueue", object())  # TypeError
          except TypeError:
              print("Failed fast as expected")

Summary
^^^^^^^^^

* Mersal provides a comprehensive error handling system for processing messages
* Error tracking maintains the state of failed messages
* Fail-fast checking prevents unnecessary retries for certain exceptions
* The dead letter queue handles persistently failing messages
* Default implementations work out of the box, but all components are customizable
