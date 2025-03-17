Outbox
======

Introduction
-------------

When handling a message, it's typical to send messages (send commands or publish events) to various Mersal apps (including the local app that is currently handling the message). There can be two scenarios where the final outcome results in a broken state.

#. Message handling fails (e.g. data is not persisted) but the messages are sent.

#. Message handling succeeds but the sent messages fail.

Both are undesirable states; the first can result in publishing false information to other systems (e.g. ``RegisterStudentMessageHandler`` that fails to persist data but publishes a ``StudentRegisteredEvent`` to other systems). The second will lead to broken business processes (e.g a *finance* system that is subscribing to ``StudentRegisteredEvent`` to complete financial registration will fail to function.)

The solution is to persist outgoing messages along the business data using the same persistence transaction. A successful transaction means the business data **and** the outgoing messages are stored. A failed transactions means **nothing** is stored.

The outgoing messages are said to be stored in an *outbox* hence the name :term:`"Outbox pattern" <outbox>`

Since there needs to be a transaction, using the outbox pattern requires a persistence mechanism that supports atomic transactions (see :footcite:p:`2021:khononov` [page 145-146] for implementing this pattern with NoSQL databases).

Usage
-------

Notes
^^^^^^

The outbox pattern can be used in Mersal by passing an instance of :class:`OutboxConfig <.outbox.OutboxConfig>` during initialization. The configuration requires an outbox persistence mechanism that implements :class:`OutboxStorage <.outbox.OutboxStorage>`.

.. code-block:: python

    # incomplete code

    from mersal.outbox import OutboxConfig
    from mersal.app import Mersal

    app = Mersal(outbox_config=OutboxConfig(...))

Provided implementation of  ``OutboxStorage``:

* :class:`SQLAlchemyOutboxStorage <.contrib.sqlalchemy.sqlalchemy_outbox_storage.SQLAlchemyOutboxStorage>`
* :class:`InMemoryOutboxStorage <.outbox.in_memory.InMemoryOutboxStorage>`, only used for testing since it has no concept of a transaction.

When using the outbox feature, it's important to not commit nor close the database transaction within the message handlers. That action should be handled by the outbox storage or during the :doc:`unit of work </usage/unit_of_work>` step.

Examples
^^^^^^^^^

.. dropdown:: Outbox with SQLAlchemy

  .. literalinclude:: /examples/src/mersal_docs/outbox/outbox_sqlalchemy_example.py
    :caption: outbox_sqlalchemy.py
    :name: outbox_sqlalchemy.py
    :language: python
    :emphasize-lines: 59-60,90-91
    :linenos:

  Looking at the emphasized lines, the database session is created upon handling the message. This same session needs to be shared with the outbox storage. This is done using the transaction context as shown. Other configurations are possible.

.. dropdown:: Outbox with Unit of Work (SQLAlchemy Unit of Work)

  TODO

.. dropdown:: Outbox with Idempotency

  TODO

Summary
^^^^^^^^^

* Don't close the database transaction in the message handler.
* Use Mersal idempotency feature with the outbox feature. Set it to completely skip message handling.
* Preferable to use the outbox feature with the unit of work pattern.


Internal Implementation
-----------------------

Once the outgoing messages are persisted in the outbox. A relay checks the outbox at a fixed interval for any stored messages (currently set at 1 second).

Ref :footcite:p:`2021:khononov` and :footcite:p:`microservices.io:outbox` discuss the implementation and alternatives. One alternative is a push based relay. This type of relay needs to be supported by the database.

Road Map
----------

See `Outbox Project <https://github.com/orgs/mersal-org/projects/1>`_


References
-----------

.. footbibliography::

Further Reading
----------------

.. bibliography::
   :list: bullet
   :filter: off

   nservicebus:outbox
   rebus:outbox
   brighter:outbox
