Mersal
=======

.. list-table::
   :header-rows: 1

   * - Project
     - Status
   * - CI/CD
     - .. image:: https://github.com/mersal-org/mersal/actions/workflows/publish.yml/badge.svg
          :target: https://github.com/mersal-org/mersal/actions/workflows/publish.yml
          :alt: Latest Release
       .. image:: https://github.com/mersal-org/mersal/actions/workflows/ci.yml/badge.svg
          :target: https://github.com/mersal-org/mersal/actions/workflows/ci.yml
          :alt: CI
       .. image:: https://github.com/mersal-org/mersal/actions/workflows/docs.yml/badge.svg?branch=main
          :target: https://github.com/mersal-org/mersal/actions/workflows/docs.yml
          :alt: Documentation Building
   * - Quality
     - .. image:: https://codecov.io/github/mersal-org/mersal/graph/badge.svg?token=3219SZABYN
          :target: https://codecov.io/github/mersal-org/mersal
   * - Package
     - .. image:: https://img.shields.io/pypi/v/mersal?labelColor=202235&color=1e4b94&logo=python&logoColor=white
          :target: https://badge.fury.io/py/mersal
          :alt: PyPI - Version
       .. image:: https://img.shields.io/pypi/pyversions/mersal?labelColor=202235&color=1e4b94&logo=python&logoColor=white
          :alt: PyPI - Support Python Versions
       .. image:: https://img.shields.io/pypi/dm/mersal?logo=python&label=package%20downloads&labelColor=202235&color=1e4b94&logoColor=white
          :alt: Mersal PyPI - Downloads
   * - Meta
     - .. image:: https://img.shields.io/badge/license-MIT-202235.svg?logo=python&labelColor=202235&color=1e4b94&logoColor=white
          :target: https://spdx.org/licenses/
          :alt: License - MIT
       .. image:: https://img.shields.io/badge/types-ty-202235.svg?logo=python&labelColor=202235&color=1e4b94&logoColor=white
          :target: https://github.com/astral-sh/ty
          :alt: types - ty
       .. image:: https://img.shields.io/badge/types-Basedpyright-202235.svg?logo=python&labelColor=202235&color=1e4b94&logoColor=white
          :target: https://github.com/DetachHead/basedpyright
          :alt: types - Basedpyright
       .. image:: https://img.shields.io/badge/types-Mypy-202235.svg?logo=python&labelColor=202235&color=1e4b94&logoColor=white
          :target: https://github.com/python/mypy
          :alt: types - Mypy
       .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json&labelColor=202235&color=1e4b94
          :target: https://github.com/astral-sh/ruff
          :alt: linting - Ruff

**Mersal** is a service bus library for Python. It helps you build message driven systems (a.k.a event driven architecture).

There will be more here eventually but here is an LLM summary of core features in Mersal:

* **Transport agnostic**: AWS SNS/SQS, GCP Pub/Sub, RabbitMQ, Azure Servicebus, it's your choice!
* **Pub/sub** - subscribe to events across independently running apps, with
  autosubscribe support so wiring stays out of your way.
* **Sagas** - coordinate a business process that spans multiple messages
  over time, with pluggable storage for the saga's state.
* **The outbox pattern** - persist outgoing messages in the same transaction
  as your business data, so a handler's side effects and its database write
  succeed or fail together.
* **Idempotent handling** - process the same message more than once without
  corrupting state.
* **Retries and error handling** - configurable retry strategies with
  dead-lettering to an error queue once a message keeps failing, so nothing
  is silently dropped.
* **A transport bridge** - route messages to specific destinations through a
  different transport than the rest of the system, useful for migrations,
  cost/efficiency tradeoffs, or testing.
* **Pluggable persistence, and serialization**
* **Unit of work and a request/response-style pipeline** - hook into message
  handling to add your own cross-cutting behavior, the same way middleware
  works in a web framework.

Head to the `quick start <https://docs.mersal.dev/latest/quickstart.html>`_ to
build a small message-driven system in a few minutes, or the full
`documentation <https://docs.mersal.dev>`_ for everything else.

Acknowledgments ♥
-------------------

This is a personal acknowledgment from myself (@abdulhaq-e), the main author of Mersal.

First, to the book `Architecture Patterns with Python
<https://www.cosmicpython.com/>`_ ("Cosmic Python") and its two authors,
Harry Percival (@hjwp) and Bob Gregory (@bobthemighty). Its
impact on my career is substantial and cannot be compared to any other material
I came by. In addition, the book is why we have Mersal.

I was following the book before its official release via its git repository. I
completed every example, studied all patterns, read all the side material and
years later, I still go back to it. It is like watching and rewatching a
favourite TV show! I really recommend anyone who is building systems using
Python (or any other language actually) to study from this book, especially if
someone wants to adopt Domain Driven Design (DDD).

In Part 2 of the book, the authors introduce the concept of Event Driven
Architecture and the idea of a "message bus". Once I started building a system
and applying my learnings, the system message bus was more or less the message
bus from the book. From one system to the next, the bus was extracted into a
reusable package and for years it was "pyservicebus". This now brings me to the
second acknowledgment. Before that, thank you, Harry and Bob, for writing the
book, and for putting so much effort into it and for writing/releasing it as an
open book.  ♥

The current state of Mersal is significantly different than how `pyservicebus`
looked like. I still have the commits stored somewhere with all the cursing and
trials.  Building a service bus that abstracts transport mechanism isn't an easy
job. So why not build on the shoulder of giants. While learning more about the
concept of a message bus, I did come by NServiceBus and they have great learning
materials regarding the topic and message driven architecture in general.
NServicebus is OSS but their product is what you can consider as a gigantic
framework with all batteries included. When looking for inspiration for Mersal,
I wanted something lighter and that's when I found `Rebus
<https://github.com/rebus-org>`_, it's a .NET service bus designed to provide a
"lean" offering. While Mersal might have drifted since, I'd still agree to
call it the "Python replica of Rebus". Huge thanks to Mogens Heller Grabe
(@mookid8000), Rebus's core developer, for building and maintaining it so
well for so long that it was worth learning from and borrowing this much
from. ♥

Finally, a shout out to `Litestar <https://github.com/litestar-org>`_. A
number of things in Mersal, from small utilities to bigger design decisions,
were copied or heavily inspired by code in the Litestar organization's
repositories. Thanks to everyone there for building something worth learning
from and borrowing from as well.
