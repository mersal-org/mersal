Transactions
============

..
   .. note::
      This page is a placeholder for transaction documentation. It will be expanded in future updates.

   Transactions in Mersal provide a way to ensure that message processing operations are atomic and reliable.

   Overview
   --------

   Transaction contexts in Mersal help coordinate operations across different parts of the system, ensuring that
   messages are properly processed, acknowledged, and committed or rolled back as a unit.

   Basic Usage
   ----------

   .. code-block:: python

       from mersal.transport import DefaultTransactionContextWithOwningApp

       # Using an explicit transaction context
       async with DefaultTransactionContextWithOwningApp(app) as transaction_context:
           await app.send(message)
           # Other operations within the same transaction...
           # The transaction will be committed automatically at the end of the context

   More details on transactions will be added in future documentation updates.
