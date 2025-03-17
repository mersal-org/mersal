Idempotency
=============

Introduction
-------------

Using message queues cannot guarantee that messages will only be delivered once. A lot has been written on this, see refs :footcite:p:`bravenewgeek:delivery`, :footcite:p:`bravenewgeek:tadeoffs` and :footcite:p:`rebus:delivery`.  This means that special care must be given to handling repeated messages. The handling of messages has to be :term:`idempotent <idempotent>`

Idempotency can be achieved using two methods

#. Making the message handler(s) themselves idempotent.

   This can be achieved by using tools like soft deletes, `upsert <https://www.cockroachlabs.com/blog/sql-upsert>`_.

   It is not always doable and it might not be worth changing code paradigm just to achieve idempotency.

#. Track the messages that were already handled.

   A persistence storage is made to track handled messages. This storage can be queried to check if the message has already been processed. At the end of message handling, the message identifier is persisted to indicate that the message has being processed. Mersal makes it easy to use this form of idempotency.

   For this to be used, the persistence infrastructure must support atomic transactions. The message has to be set as proceeded in the same transaction that persists the business data.

Usage
-------

Notes
^^^^^^

Configuration
""""""""""""""""

The idempotency feature can be used in Mersal by passing an instance of :class:`IdempotencyConfig <.idempotency.IdempotencyConfig>` during initialization.


.. code-block:: python

    # incomplete code

    from mersal.unit_of_work import IdempotencyConfig
    from mersal.app import Mersal

    app = Mersal(idempotency=IdempotencyConfig(...))


The configuration takes an instance of :class:`MessageTracker <.idempotency.MessageTracker>` that implements querying tracked messages and setting messages as tracked. It also takes another boolean argument `should_stop_invocation` that will be explained below.

Currently only a testing implementations of `MessageTracker` is provided:

* :class:`InMemoryMessageTracker <.persistence.in_memory.in_memory_message_tracker.InMemoryMessageTracker>`, it's for testing only because it has no concept of a "transaction".

A SQLAlchemy message tracker will be implemented :ref:`next <Idempotency Road Map>`.

should_stop_invocation
""""""""""""""""""""""""

How to handle a repeated message? Should it even be handled or should it be completely ignored? This is what the setting `should_stop_invocation` controls.

#. `should_stop_invocation=True`

   All the message handlers for all messages will be skipped. Not recommended when **not using** the outbox feature. Here is why:

   .. code-block:: python
    :linenos:
    :emphasize-lines: 9, 12

      # incomplete code

      class MessageHandler:
          def __init__(self):
              ...

          async def __call__(self, message: Any):
              # persist some business data here:
              session.add(User("J"))

              # then publish some messages.
              self.mersal.publish(UserAdded("J"))

   For a repeated message **without** using an outbox, we are guaranteed that the business data is already persisted (since it is persisted in the same transaction as the message tracker). However, publishing the external message might have not went through for whatever reason. Therefore, completely skipping this message handler is not recommended in this case.

   If the outbox feature is used, then the outgoing published message is also guaranteed to be stored along the business data and hence it is safe to skip handling this message.

#. `should_stop_invocation=False`

   The repeated message handlers will be invoked as usual. The handler code can check if the message is repeated via the message headers.

   .. code-block:: python
    :linenos:
    :emphasize-lines: 11

      # incomplete code

      from mersal.idempotency import IDEMPOTENCY_CHECK_KEY

      class MessageHandler:
          def __init__(self):
              ...

          async def __call__(self, message: Any):

              if not message.headers.get(IDEMPOTENCY_CHECK_KEY):
                # persist some business data here:
                # session.add(User("J"))

              # then publish some messages.
              self.mersal.publish(UserAdded("J"))

   The header value (emphasized line) can be used to control the behaviour of handling repeated messages. A value of `True` means the message is repeated.


Examples
^^^^^^^^^

.. dropdown:: Idempotency with InMemoryMessageTracker

  TODO


Summary
^^^^^^^^^

* Don't close the database transaction in the message handler.
* When using the idempotency feature **without** the outbox feature; check the idempotency key to skip the business logic that is related to persisting business data but ALWAYS resend/publish outgoing messages.
* When using the idempotency feature with the outbox feature; it is safe to set `should_stop_invocation=True` to skip handling repeated messages.

Internal Implementation
-----------------------

N/A


.. _Idempotency Road Map:

Road Map
----------

See `Idempotency Project <https://github.com/orgs/mersal-org/projects/3>`_

References
-----------
.. footbibliography::

Further Reading
----------------

.. bibliography::
   :list: bullet
   :filter: off

   lostechies:unreliability
   sapenworks:idempotency
   particular:idempotent
