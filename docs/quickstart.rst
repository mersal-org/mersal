Quick Start
============

In this quick start, we will build a simple message driven system using Mersal. It should only take a few minutes. We won't use a production ready setup nor will we dive deep into how things work. This is just an appetizer. If you are already familiar with message driven systems or want a deeper dive, then one of the :doc:`tutorials <tutorials/index>` would be a better fit.

.. admonition:: No more e-commerce examples please
   :collapsible: closed

   If you open a random blog post or tutorial or some sample source code that explains a topic related to distributed systems or message/event driven architecture, the most likely scenario you will find is an e-commerce example. If you went through a lot of these, you will probably say "oh not e-commerce again" once you start reading our quick start guide here.

   We agree, it has become a boring example (despite being very challenging and an excellent use case for demonstration). To avoid this cliche, we promise that **beyond** the quick start guide, we will not use an e-commerce scenario (see :doc:`example_theme` ). So, e-commerce scenario one more time only!



The scenario
-------------

An online store lets shoppers save products to a wishlist. When a product's
price drops, everyone who has that product on their wishlist should get an email.

We promised to make this a quick start guide so we won't discuss solution approaches
whether it's message driven or not so lets jump right in.

Installation
-------------

Lets create the virtual environment, assuming `uv` is used:

.. code-block:: bash

   uv init mersal-quickstart

Now lets add Mersal as a dependency

.. code-block:: bash

   cd mersal-quickstart

.. code-block:: bash

   uv add mersal


The domain
-----------

We define the two messages that will be used in our system. They can be defined using two plain dataclasses.

Lets create a file called :file:`messages.py` and place the following into it:

.. literalinclude:: /examples/src/mersal_docs/quickstart/messages.py
   :caption: messages.py
   :language: python

Mersal Apps
---------------

Lets think of our system as it's made up of multiple app. Each app is responsible for handling a certain message. A message can also be handled by multiple apps. We will call each of these as a "Mersal app".

For this system, we will have two Mersla apps, one of them will be called "catalog" and the other one will be called "notifications". Lets create them now.

Create a new file called :file:`main.py`

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python


Handling the update price message
-----------------------------------

Right now the two apps exist but neither one knows how to handle any
message. Lets fix the catalog side first:

Create a new file called :file:`update_price_message_handler.py`


.. literalinclude:: /examples/src/mersal_docs/quickstart/update_price_message_handler.py
   :language: python

The catalog's handler updates the catalog prices (in production this would be a database call), then :py:meth:`publishes
<mersal.app.Mersal.publish>` the event.

Now we need to update :file:`main.py` so that the catalog Mersal app can handle that message. Register the handler on the catalog's activator, inside ``main()``:

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python
   :pyobject: main
   :emphasize-lines: 9

Reacting to the event
-----------------------

The notifications side only needs to know about ``PriceDecreased``. It has no
idea ``UpdateProductPrice`` exists, and the catalog has no idea this handler
exists either - that's the whole point of :doc:`pub/sub <usage/pub_sub>`.

Create a new file called :file:`notify_wishlist_users_handler.py`:

.. literalinclude:: /examples/src/mersal_docs/quickstart/notify_wishlist_users_handler.py
   :caption: notify_wishlist_users_handler.py
   :language: python

Register it on the notifications app, and subscribe that app to
``PriceDecreased`` so it actually receives events the catalog publishes:

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python
   :pyobject: main
   :emphasize-lines: 10,12

Adding another consumer
--------------------------

Nothing says only one app can react to ``PriceDecreased``. Say the finance
team wants to log every price change for reporting, completely independently
of notifications. Because pub/sub decouples publishers from subscribers,
adding them is just another handler and another subscription - nothing about
the catalog or the notifications app has to change.

Create a new file called :file:`record_price_change_handler.py`:

.. literalinclude:: /examples/src/mersal_docs/quickstart/record_price_change_handler.py
   :caption: record_price_change_handler.py
   :language: python

Create a third Mersal app, register the handler, and subscribe it to
``PriceDecreased`` just like we did for notifications:

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python
   :pyobject: main
   :emphasize-lines: 7,11,13

That's the whole change. The catalog still only knows how to publish
``PriceDecreased`` - it has no idea it now has two subscribers instead of one.

Wiring it together
-------------------

The catalog, notifications, and accounting apps are three separate
:class:`Mersal <mersal.app.Mersal>` apps, each with its own queue. What lets
an event published by one reach subscribers registered on the others is the
single ``subscription_store`` that ``make_mersal_app`` was handed for all
three - no extra wiring needed beyond passing the same store to every app.

Sending the first message
---------------------------

All three apps know how to handle their messages now. Something still has to
put an ``UpdateProductPrice`` command on the catalog's queue in the first
place. In a real system, that trigger usually comes from one of:

* **A legacy or external system** - some other piece of infrastructure
  already writes messages compatible with the transport directly onto the
  queue, without going through Mersal at all.
* **Manually placing one** - handy while developing or debugging. Our
  transport is just JSON files on disk, so dropping a file like this into
  ``.mersal-quickstart/catalog/`` is enough for it to get picked up:

  .. code-block:: json
     :caption: .mersal-quickstart/catalog/manual-message.json

     {
       "headers": {"message_id": "11111111-1111-1111-1111-111111111111"},
       "body": "{\"type\": \"UpdateProductPrice\", \"data\": {\"product_id\": \"product-42\", \"new_price\": 799.0}}",
       "body_type": "json"
     }

* **Mersal itself** - most commonly, some other part of your app calls
  :py:meth:`send_local <mersal.app.Mersal.send_local>` or :py:meth:`send
  <mersal.app.Mersal.send>`, for example from an HTTP endpoint right after it
  receives a request to change a product's price.

For this quick start we'll take the third route, and we'll do it from a
second, separate script. ``main.py`` is a *worker*: its only job is to host
handlers and process whatever shows up on a queue, so it never places
anything on one itself. Placing a message is a different concern, so it gets
its own file.

.. admonition:: Why bother with two files?
   :collapsible: closed

   Nothing about Mersal requires this split - the same Python process that
   runs a worker can just as easily call ``send_local`` itself, for example
   from an HTTP handler that also happens to host the catalog worker. We're
   using two scripts here only so the quick start makes the boundary
   obvious: *hosting handlers* (what ``start()`` does) and *placing a
   message on a queue* (what ``send_local``/``send``/``publish`` do) are
   independent things, and you only ever need the one you're actually doing.

Create a new file called :file:`send_price_update.py`:

.. literalinclude:: /examples/src/mersal_docs/quickstart/send_price_update.py
   :caption: send_price_update.py
   :language: python

Notice ``make_mersal_app("catalog", ...)`` here is the exact same call
``main.py`` makes for the catalog app - same name, same transport, same
serializer, so it resolves to the same queue on disk. The only difference is
that this script never calls ``catalog_app.start()``. Starting is what turns
an app into a worker that pulls messages off its queue and dispatches them to
handlers; skip it, and the app object can still place a message on a queue
just fine, it simply won't be the one to pick anything up.

Now, a question worth asking before we send anything: what should happen if
the notifications app happens to be down, mid-deploy, or just plain buggy at
the moment the price changes? Should the catalog wait for it? It shouldn't
have to - and with Mersal it doesn't.

To show that, ``main.py`` accepts ``--catalog`` and ``--notifications`` flags
that control which of those two apps actually starts (accounting always
starts - this isn't about accounting, it's here to prove the other two don't
need each other). Passing neither flag starts everything, which is the normal
case:

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python
   :start-at: if __name__ == "__main__":

A real worker doesn't do its job once and exit - it keeps its workers running
so it can keep handling whatever shows up next:

.. literalinclude:: /examples/src/mersal_docs/quickstart/main.py
   :caption: main.py
   :language: python
   :pyobject: main
   :emphasize-lines: 15-19

Running it
----------

Start the worker in one terminal and leave it running:

.. code-block:: bash

   uv run main.py

.. code-block:: text

   Running. Press Ctrl+C to stop.

Then, in a second terminal, send the price update:

.. code-block:: bash

   uv run send_price_update.py

Back in the first terminal, the worker's output appears as soon as the
message is picked up:

.. code-block:: text

   [catalog] product-42 is now $799.00
   [accounting] Logged price change for product-42: now $799.00
   [notifications] Emailing ada@example.com: product-42 dropped to $799.00
   [notifications] Emailing grace@example.com: product-42 dropped to $799.00

The worker keeps running after that - press Ctrl+C in its terminal when
you're done watching it. ``send_price_update.py`` has already exited on its
own; it only ever had one message to send.

What you just built
--------------------

* A **command** (``UpdateProductPrice``) sent straight to one app with
  :py:meth:`send_local <mersal.app.Mersal.send_local>`.
* An **event** (``PriceDecreased``) published with
  :py:meth:`publish <mersal.app.Mersal.publish>` and delivered to whoever is
  subscribed, without the publisher knowing who that is.
* Three independent :class:`Mersal <mersal.app.Mersal>` apps, each running
  their own worker loop, coordinating only through messages - notifications
  and accounting were added without ever touching the catalog.

What happens when it fails?
----------------------------

Real email providers go down. Let's see what happens when the notifications
handler always fails. Add this next to ``NotifyWishlistUsersHandler`` in
:file:`notify_wishlist_users_handler.py`:

.. literalinclude:: /examples/src/mersal_docs/quickstart/notify_wishlist_users_handler.py
   :caption: notify_wishlist_users_handler.py
   :pyobject: FlakyNotifyWishlistUsersHandler
   :language: python

Then, in :file:`main.py`, register that one instead:

.. code-block:: python
   :caption: main.py

   notifications_activator.register(PriceDecreased, lambda _, __: FlakyNotifyWishlistUsersHandler())

Nothing else changes - no retry configuration, no error queue setup. Mersal's
defaults (:class:`RetryStrategySettings <mersal.retry.RetryStrategySettings>`)
already give every app 5 attempts per message before moving it to a queue
named ``"error"``:

Start the worker, then send the price update from the second terminal just
like before:

.. code-block:: bash

   uv run main.py

.. code-block:: bash

   uv run send_price_update.py

Back in the worker's terminal:

.. code-block:: text

   [catalog] product-42 is now $799.00
   [accounting] Logged price change for product-42: now $799.00
   [notifications] Attempt 1: emailing wishlist for product-42...
   [notifications] Attempt 2: emailing wishlist for product-42...
   [notifications] Attempt 3: emailing wishlist for product-42...
   [notifications] Attempt 4: emailing wishlist for product-42...
   [notifications] Attempt 5: emailing wishlist for product-42...

Notice that accounting logs the price change just fine - it's a completely
separate subscriber, so notifications failing and retrying has no effect on
it whatsoever. Press Ctrl+C to stop the process once the retries are done.

.. dropdown:: What's actually in .mersal-quickstart/error/

   .. code-block:: json

      {
        "headers": {
          "message_id": "d64ff89c-b08d-48b3-91aa-5ba2b4e8ac36",
          "sent_time": "2026-07-23T23:10:44.972092+00:00",
          "correlation_id": "4e14981e-3116-47c7-a53b-e92c729dd3fb",
          "correlation_sequence": "1",
          "causation_id": "4e14981e-3116-47c7-a53b-e92c729dd3fb",
          "error_details": "SendGrid API is currently unreachable!--SendGrid API is currently unreachable!--..."
        },
        "body": "{\"type\": \"PriceDecreased\", \"data\": {\"product_id\": \"product-42\", \"new_price\": 799.0}}",
        "body_type": "json"
      }

   The catalog's price update already committed - it never knew or cared that
   notifications were failing. The event itself isn't lost either: it's
   sitting in ``error/`` with the exception recorded in its headers, ready to
   be inspected and replayed once the email provider is back.

   To customize the retry count or error queue name, pass
   ``retry_strategy_settings=RetryStrategySettings(...)`` to ``Mersal(...)`` -
   see :doc:`usage/error_handling`.

Revert the registration line back to ``NotifyWishlistUsersHandler`` before
moving on.

Running one app without the other
------------------------------------

The ``--catalog`` and ``--notifications`` flags let us simulate the
notifications app being down without touching any code. Start only the
catalog (and accounting) side:

.. code-block:: bash

   uv run main.py --catalog

Then, from the second terminal, send the price update as before:

.. code-block:: bash

   uv run send_price_update.py

Back in the worker's terminal:

.. code-block:: text

   [catalog] product-42 is now $799.00
   [accounting] Logged price change for product-42: now $799.00

Notifications never started, so nothing was there to receive the
``PriceDecreased`` event - but it wasn't dropped either. Because
``notifications_app.subscribe(PriceDecreased)`` had already registered its
queue address with the shared ``subscription_store``, the catalog delivered
the event straight onto disk at ``.mersal-quickstart/notifications/``, where
it sits waiting. Press Ctrl+C to stop this run.

Now start only notifications:

.. code-block:: bash

   uv run main.py --notifications

.. code-block:: text

   [notifications] Emailing ada@example.com: product-42 dropped to $799.00
   [notifications] Emailing grace@example.com: product-42 dropped to $799.00
   Running. Press Ctrl+C to stop.

Accounting has nothing new to log this time - it already picked up and
processed its copy of the event during the first run, since it starts
unconditionally regardless of which flags are passed. Notifications, on the
other hand, picks up the event it had backlogged: no message was lost while
it was "down". This is the same durability at work as the error queue:
messages live on the transport, not in memory, so a subscriber can subscribe
long before it ever starts, and catch up on whatever accumulated once it
does.

Sending before any worker exists
------------------------------------

Every run so far started ``main.py`` first and sent the update second. Take
that further: what if the catalog worker has never run at all - not down
mid-deploy, not restarting, just never started once - when the price update
needs to go out?

Send the update with nothing running:

.. code-block:: bash

   uv run send_price_update.py

Nothing prints, and there's no error. The command connected to the catalog's
queue on disk, wrote ``UpdateProductPrice`` into it, and exited - it never
needed a worker to be listening.

Now start the worker, whenever that happens to be:

.. code-block:: bash

   uv run main.py

.. code-block:: text

   [catalog] product-42 is now $799.00
   [accounting] Logged price change for product-42: now $799.00
   [notifications] Emailing ada@example.com: product-42 dropped to $799.00
   [notifications] Emailing grace@example.com: product-42 dropped to $799.00
   Running. Press Ctrl+C to stop.

The instant the catalog worker comes online it finds the message that was
already waiting, and the whole chain fires from there: the price update gets
handled, ``PriceDecreased`` gets published, and both accounting and
notifications react - despite the fact that none of these three apps existed
as a running process at the moment the message was sent. The queue is a
directory on disk, not an in-memory mailbox held by a running app, so there's
nothing for a sender to wait on and no ordering requirement between "a worker
exists" and "a message arrives for it."

Press Ctrl+C to stop the worker once you're done watching it.

Next steps
----------

* :doc:`usage/pub_sub` - subscriptions, topics, and autosubscribe
* :doc:`usage/error_handling` - customizing retries, fail-fast exceptions, and
  dead-letter handling
* :doc:`usage/index` - transports, unit of work, sagas, and everything else
