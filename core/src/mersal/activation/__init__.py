"""Message handler activation module.

This module provides classes for registering and activating message handlers
based on message types. The handler activator pattern is core to how Mersal
dispatches messages to the appropriate handlers.
"""

from mersal._activation.builtin_handler_activator import BuiltinHandlerActivator
from mersal._activation.handler_activator import HandlerActivator

__all__ = (
    "BuiltinHandlerActivator",
    "HandlerActivator",
)
