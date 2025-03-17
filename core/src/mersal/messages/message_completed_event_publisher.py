from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from .message_completed_event import MessageCompletedEvent

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mersal.app import Mersal
    from mersal.pipeline import MessageContext
    from mersal.types import AsyncAnyCallable

__all__ = ("message_completed_event_publisher",)


def message_completed_event_publisher(
    message_context: MessageContext,
    app: Mersal,
    _: list[AsyncAnyCallable],
) -> Callable[[object], Awaitable[None]]:
    async def handler(_: object) -> None:
        completed_message_id = message_context.headers.message_id
        published_message_id = uuid.uuid4()
        await app.publish(
            MessageCompletedEvent(completed_message_id=completed_message_id),
            headers={"message_id": published_message_id},
        )

    return handler
