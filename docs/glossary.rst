Glossary
========

.. glossary::

   outbox

    a pattern used in distributed systems to reliably send messages within message handling.

    .. seealso::

        :doc:`Using Outbox </usage/outbox>`


   idempotent

     an idempotent operation always causes the same result. For messaging systems, this means handling the same message multiple times should always result in the same state.

     .. seealso::

        :doc:`Idempotency </usage/idempotency>`

   send-only

     an app that only sends or publishes messages and never receives any. It has no worker polling the transport, and its transport may skip setting up resources (e.g. an input queue) that are only needed for receiving.

     .. seealso::

        :ref:`Send-only Apps <send_only_apps>`
