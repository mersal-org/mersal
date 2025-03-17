Unit of Work
==============

Introduction
-------------

The usual preferred outcome after handling a message is to either commit all the changes or rollback all the changes. This is to ensure atomic operations.

While some database systems provide this via atomic transactions, the concept of "committing" is not just relevant to databases.

A message handler might have some other non-db side-effect that is executed immediately but then has to be reversed if a rollback happens. Another example would be a message that is handled by multiple handlers, having the unit of work ensures the work done by all handlers to be committed altogether or none at all (this can be done other ways as well, for example; sharing the database transaction between the handlers which is what the uow is doing anyway!)

There can be other scenarios but in short; the unit of work pattern allows message handling to be wrapped in a transaction. If the transaction is committed/rolledback then certain actions  can be executed (usually database related actions).


Usage
-------

Notes
^^^^^^

Initialization
""""""""""""""""

The unit of work pattern can be used in Mersal by passing an instance of :class:`UnitOfWorkConfig <.unit_of_work.UnitOfWorkConfig>` during initialization.


.. code-block:: python

    # incomplete code

    from mersal.unit_of_work import UnitOfWorkConfig
    from mersal.app import Mersal

    app = Mersal(unit_of_work=UnitOfWorkConfig(...))


The config requires several inputs, how to create the unit of work object, what to do on commit/rollback/close. The examples below will show a usecase of :class:`SQLAlchemyUnitOfWork <.contrib.sqlalchemy.SQLAlchemyUnitOfWork>` that is provided and ready to be used.

Accessing the unit of work
""""""""""""""""""""""""""""

The unit of work object will be injected in :class:`TransactionContext <.transport.TransactionContext>` using the key `"uow"`. This is useful as it can be retrieved within message handlers.

.. code-block:: python

    # incomplete code,

    from mersal.transport import TransactionContext
    from mersal.pipeline import MessageContext

    class MessageHandler:
        def __init__(message_context: MessageContext):
            self.message_context = message_context

        async def __call__(self, message):
            transaction_context = self.message_context.transaction_context
            uow = transaction_context.items["uow"]


It's important to not commit the unit of work within a message handler or commit/cancel the database connection it may contain.

`commit_with_transaction`
""""""""""""""""""""""""""""


It is worth noting what the `commit_with_transaction` property means in `UnitOfWorkConfig` (this property should probably be clarified/renamed, too many "transactions" words being thrown around). `commit_with_transaction` refers to the point at which the unit of work commit/rollback happens. By default, this is set to `False` which means that the unit of work commit will be called after all the message handlers are invoked but *before* the :class:`TransactionContext <.transport.TransactionContext>` is committed. If this is set to `True`, the unit of work will only commit as part of the `TransactionContext` commit actions.

Without including any other features, changing `commit_with_transaction` makes no difference. However, when using :doc:`Outbox </usage/outbox>` or :doc:`Idempotency </usage/idempotency>`, then `commit_with_transaction` must be set to `True`. Those features are implemented using the `TransactionContext` commit actions. If the unit of works commits early (i.e when `commit_with_transaction` is `False`), then those features will not work!

Examples
^^^^^^^^^


.. dropdown:: Unit of Work with SQLAlchemy


  .. literalinclude:: /examples/src/mersal_docs/unit_of_work/unit_of_work_sqlalchemy_example.py
    :caption: unit_of_work_sqlalchemy.py
    :name: unit_of_work_sqlalchemy.py
    :language: python
    :emphasize-lines: 51-53,67,70,91
    :linenos:

  Looking at the emphasized lines, the database session is created inside the unit of work. This unit of work is then accessed in the message handler. It contains the session to interact with the database.


Summary
^^^^^^^^^

* Remember to set `commit_with_transaction=True` when using the outbox or idempotency features.

Internal Implementation
-----------------------

N/A

Road Map
----------

See `Unit of Work Project <https://github.com/orgs/mersal-org/projects/2>`_

References
-----------

.. footbibliography::

Further Reading
----------------

.. bibliography::
   :list: bullet
   :filter: off

   2020:percival:cosmicpython
   fowler:unitofwork
   nservicebus:unitofwork
   rebus:unitofwork
