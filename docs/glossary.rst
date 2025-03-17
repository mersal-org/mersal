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
