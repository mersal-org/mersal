Transport Bridge
===================

Introduction
-------------

It is very likely that a system compromised of multiple Mersal apps to be relying on the same transport. However, there might be a need to use different transports for specific destinations (queues). Reasons may vary, below are some examples:

#. The new project is using RabbitMQ but legacy parts of the system are using ActiveMQ.
#. Requiring one part of the system to use a different transport to save cost or have better efficiency (it doesn't have to be a different transport technology, it might a separate server of the same transport technology)
#. Testing; tests are great, being able to send messages using a different transport allows for easier testing of pub/sub (see example below).

To allow the above, a :class:`TransportBridge <.transport.TransportBridge>` has been created. It wraps a transport in addition to allowing messages sent to specific addresses to use a different transport.

Usage
-------

Notes
^^^^^^


Examples
^^^^^^^^^

.. dropdown:: Spying on sent messages

  ..
     .. literalinclude:: /examples/mersal_docs/outbox/outbox_sqlalchemy_example.py
       :caption: outbox_sqlalchemy.py
       :name: outbox_sqlalchemy.py
       :language: python
       :emphasize-lines: 59-60,90-91
       :linenos:

  TODO



Summary
^^^^^^^^^

N/A

Internal Implementation
-----------------------

N/A

Road Map
----------

N/A


References
-----------

.. footbibliography::

Further Reading
----------------

.. bibliography::
   :list: bullet
   :filter: off
