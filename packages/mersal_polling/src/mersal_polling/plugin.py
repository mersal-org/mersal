from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mersal.activation import HandlerActivator
from mersal.lifespan import LifespanHandler
from mersal.messages import MessageCompletedEvent
from mersal.plugins import Plugin
from mersal.retry import ErrorHandler
from mersal_polling.error_handler_poller_wrapper import (
    ErrorHandlerPollerWrapper,
)
from mersal_polling.message_completion_handler import register_message_completion_publishers

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mersal.app import Mersal
    from mersal.configuration import StandardConfigurator
    from mersal.pipeline.message_context import MessageContext
    from mersal_polling.config import (
        FailedCompletionCorrelation,
        PollingConfig,
        SuccessfulCompletionCorrelation,
    )

__all__ = ("PollingPlugin",)


class PollingPlugin(Plugin):
    """Plugin that adds polling functionality to a Mersal application.

    This plugin enables waiting for message processing completion through polling.
    It registers handlers for MessageCompletedEvent and custom completion events,
    and can automatically add completion event publishers for registered message types.
    """

    def __init__(self, config: PollingConfig) -> None:
        """Initialize a new polling plugin.

        Args:
            config: The configuration for the polling plugin
        """
        self._poller = config.poller
        self._successfull_completion_events_map = config.successful_completion_events_map
        self._failed_completion_events_map = config.failed_completion_events_map
        self._auto_publish_completion_events = config.auto_publish_completion_events
        self._exclude_from_completion_events = config.exclude_from_completion_events

    def __call__(self, configurator: StandardConfigurator) -> None:
        """Configure the Mersal application with polling functionality.

        Args:
            configurator: The standard configurator for the application
        """
        # Configure event subscriptions for MessageCompletedEvent and other events
        self._configure_event_subscriptions(configurator)

        # Integrate with error handling
        self._configure_error_handler(configurator)

        # Register handlers for completion events
        self._configure_completion_event_handlers(configurator)

        # If auto-publish is enabled, register completion event publishers for all message types
        if self._auto_publish_completion_events:
            self._configure_auto_completion_event_publishing(configurator)

    def _configure_event_subscriptions(self, configurator: StandardConfigurator) -> None:
        """Configure event subscriptions for the polling plugin.

        Args:
            configurator: The standard configurator for the application
        """

        def decorate(configurator: StandardConfigurator) -> Any:
            events_to_subscribe_to: list[type] = [
                MessageCompletedEvent,
            ]
            lifespan_handler: LifespanHandler = configurator.get(LifespanHandler)  # type: ignore[type-abstract]
            app: Mersal = configurator.mersal

            # Add all custom completion events
            for event in self._successfull_completion_events_map:
                events_to_subscribe_to.append(event)
            for event in self._failed_completion_events_map:
                events_to_subscribe_to.append(event)

            # Register a startup hook to subscribe to all events
            lifespan_handler.register_on_startup_hook(self._subscribe(app, events_to_subscribe_to))  # type: ignore[arg-type]

            return lifespan_handler

        configurator.decorate(LifespanHandler, decorate)

    def _configure_error_handler(self, configurator: StandardConfigurator) -> None:
        """Configure error handling integration with polling.

        Args:
            configurator: The standard configurator for the application
        """

        def decorate_error_handler(configurator: StandardConfigurator) -> Any:
            error_handler: ErrorHandler = configurator.get(ErrorHandler)  # type: ignore[type-abstract]
            return ErrorHandlerPollerWrapper(self._poller, error_handler)

        configurator.decorate(ErrorHandler, decorate_error_handler)

    def _configure_completion_event_handlers(self, configurator: StandardConfigurator) -> None:
        """Configure handlers for message completion events.

        Args:
            configurator: The standard configurator for the application
        """

        def decorate_activator(configurator: StandardConfigurator) -> Any:
            activator: HandlerActivator = configurator.get(HandlerActivator)  # type: ignore[type-abstract]

            # Register handler for MessageCompletedEvent
            activator.register(
                MessageCompletedEvent,
                lambda __, _: self._message_completed_event_handler,
            )

            # Register handlers for custom success completion events
            for (
                event_type,
                success_correlator,
            ) in self._successfull_completion_events_map.items():
                activator.register(
                    event_type,
                    lambda message_context,  # type: ignore[misc]
                    _,
                    sc=success_correlator: self._successfull_custom_completion_event_handler_factory(
                        sc, message_context
                    ),
                )

            # Register handlers for custom failure completion events
            for (
                event_type,
                failure_correlator,
            ) in self._failed_completion_events_map.items():
                activator.register(
                    event_type,
                    lambda message_context,  # type: ignore[misc]
                    _,
                    fc=failure_correlator: self._failed_custom_completion_event_handler_factory(fc, message_context),
                )

            return activator

        configurator.decorate(HandlerActivator, decorate_activator)

    def _configure_auto_completion_event_publishing(self, configurator: StandardConfigurator) -> None:
        """Configure automatic completion event publishing.

        Args:
            configurator: The standard configurator for the application
        """

        def decorate_activator(configurator: StandardConfigurator) -> Any:
            activator: HandlerActivator = configurator.get(HandlerActivator)  # type: ignore[type-abstract]
            register_message_completion_publishers(activator, self._exclude_from_completion_events)
            return activator

        configurator.decorate(HandlerActivator, decorate_activator)

    async def _message_completed_event_handler(self, event: MessageCompletedEvent) -> None:
        """Handle MessageCompletedEvent by updating the poller.

        Args:
            event: The message completed event
        """
        await self._poller.push(event.completed_message_id, None)

    def _successfull_custom_completion_event_handler_factory(
        self,
        correlator: SuccessfulCompletionCorrelation,
        message_context: MessageContext,
    ) -> Callable[[Any], Awaitable[None]]:
        """Create a handler for custom successful completion events.

        Args:
            correlator: The correlation configuration
            message_context: The message context

        Returns:
            A handler function that processes the event
        """

        async def _custom_completion_event_handler(event: Any) -> None:
            if message_id_getter := correlator.message_id_getter:
                message_id = message_id_getter(event)
            else:
                message_id = message_context.headers.correlation_id
            await self._poller.push(message_id, None)

        return _custom_completion_event_handler

    def _failed_custom_completion_event_handler_factory(
        self, correlator: FailedCompletionCorrelation, message_context: MessageContext
    ) -> Callable[[Any], Awaitable[None]]:
        """Create a handler for custom failure completion events.

        Args:
            correlator: The correlation configuration
            message_context: The message context

        Returns:
            A handler function that processes the event
        """

        async def _custom_completion_event_handler(event: Any) -> None:
            if message_id_getter := correlator.message_id_getter:
                message_id = message_id_getter(event)
            else:
                message_id = message_context.headers.correlation_id

            if exception_builder := correlator.exception_builder:
                exception = exception_builder(event)
            else:
                exception = Exception("Event error")
            await self._poller.push(message_id, exception)

        return _custom_completion_event_handler

    def _subscribe(self, app: Mersal, events: list[type]) -> Callable[[list[type]], Awaitable[None]]:
        """Create a function that subscribes to the given events.

        Args:
            app: The Mersal application
            events: The list of event types to subscribe to

        Returns:
            A function that performs the subscriptions
        """

        async def subscribe(
            events: list[type] = events,
        ) -> None:
            for e in events:
                await app.subscribe(e)

        return subscribe
