import logging
from collections.abc import Mapping, Sequence
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from mersal.activation import HandlerActivator
from mersal.configuration.default_plugin import DefaultPlugin
from mersal.configuration.standard_configurator import (
    InvalidConfigurationError,
    StandardConfigurator,
)
from mersal.idempotency import IdempotencyConfig, IdempotencyPlugin
from mersal.lifespan import LifespanHandler
from mersal.lifespan.autosubscribe import AutosubscribeConfig
from mersal.messages import LogicalMessage, MessageHeaders
from mersal.outbox.config import OutboxConfig
from mersal.outbox.plugin import OutboxPlugin
from mersal.persistence.in_memory import InMemorySagaStorage
from mersal.pipeline import (
    DestinationAddresses,
    MessageIdGenerator,
    OutgoingStepContext,
    PipelineInvoker,
)
from mersal.plugins import Plugin, generic_registration_plugin
from mersal.retry import (
    ErrorHandler,
    ErrorTracker,
    FailFastChecker,
    RetryStrategySettings,
)
from mersal.retry.fail_fast.default_fail_fast_checker import (
    DefaultFailFastCheckerExceptionsContainer,
)
from mersal.routing import Router
from mersal.routing.default import DefaultRouterRegistrationConfig
from mersal.routing.default.plugin import DefaultRouterRegistrationPlugin
from mersal.sagas import SagaConfig
from mersal.sagas.plugin import SagaPlugin
from mersal.serialization import (
    MessageBodySerializer,
    MessageHeadersSerializer,
    Serializer,
)
from mersal.subscription import SubscriptionStorage
from mersal.topic import TopicNameConvention
from mersal.transport import (
    AmbientContext,
    DefaultTransactionContextWithOwningApp,
    TransactionContext,
    Transport,
)
from mersal.types import Empty, EmptyType, LifespanHook
from mersal.unit_of_work import UnitOfWorkConfig
from mersal.unit_of_work.plugin import UnitOfWorkPlugin
from mersal.utils.sync import AsyncCallable
from mersal.workers import WorkerFactory

if TYPE_CHECKING:
    from mersal.workers.worker import Worker

__all__ = ("Mersal",)


class Mersal:
    def __init__(  # noqa: C901
        self,
        name: str,
        handler_activator: HandlerActivator,
        transport: Transport | None = None,
        pipeline_invoker: PipelineInvoker | None = None,
        router: Router | None = None,
        worker_factory: WorkerFactory | None = None,
        subscription_storage: SubscriptionStorage | None = None,
        topic_name_convention: TopicNameConvention | None = None,
        on_startup_hooks: Sequence[LifespanHook] | None = None,
        on_shutdown_hooks: Sequence[LifespanHook] | None = None,
        retry_strategy_settings: RetryStrategySettings | None = None,
        error_tracker: ErrorTracker | None = None,
        error_handler: ErrorHandler | None = None,
        fail_fast_checker: FailFastChecker | None = None,
        fail_fast_exceptions: Sequence[type[Exception]] | None = None,
        plugins: Sequence[Plugin] | None = None,
        idempotency: IdempotencyConfig | None = None,
        saga: SagaConfig | EmptyType | None = None,
        serializer: Serializer | None = None,
        message_body_serializer: MessageBodySerializer | None = None,
        message_headers_serializer: MessageHeadersSerializer | None = None,
        default_router_registration: DefaultRouterRegistrationConfig | None = None,
        autosubscribe: AutosubscribeConfig | EmptyType | None = None,
        unit_of_work: UnitOfWorkConfig | None = None,
        outbox: OutboxConfig | None = None,
        pdb_on_exception: bool | None = None,
        message_id_generator: MessageIdGenerator | None = None,
    ):
        if router and default_router_registration:
            raise InvalidConfigurationError("Cannot provide both router and default_router_registration")

        if fail_fast_checker and fail_fast_exceptions:
            raise InvalidConfigurationError("Cannot provide both fail_fast_exceptions and fail_fast_checker")
        self.name = name
        self.handler_activator = handler_activator
        self.configurator = StandardConfigurator()

        plugins = list(plugins or [])
        plugins.append(generic_registration_plugin(handler_activator, HandlerActivator))
        if transport is not None:
            plugins.append(generic_registration_plugin(transport, Transport))

        if pipeline_invoker is not None:
            plugins.append(generic_registration_plugin(pipeline_invoker, PipelineInvoker))
        if router is not None:
            plugins.append(generic_registration_plugin(router, Router))
        if worker_factory is not None:
            plugins.append(generic_registration_plugin(worker_factory, WorkerFactory))
        if subscription_storage is not None:
            plugins.append(generic_registration_plugin(subscription_storage, SubscriptionStorage))
        if topic_name_convention is not None:
            plugins.append(generic_registration_plugin(topic_name_convention, TopicNameConvention))
        if retry_strategy_settings is not None:
            plugins.append(generic_registration_plugin(retry_strategy_settings, RetryStrategySettings))
        if error_tracker is not None:
            plugins.append(generic_registration_plugin(error_tracker, ErrorTracker))
        if error_handler is not None:
            plugins.append(generic_registration_plugin(error_handler, ErrorHandler))
        if fail_fast_checker is not None:
            plugins.append(generic_registration_plugin(fail_fast_checker, FailFastChecker))
        if fail_fast_exceptions is not None:
            plugins.append(
                generic_registration_plugin(
                    DefaultFailFastCheckerExceptionsContainer(exceptions=fail_fast_exceptions),
                    DefaultFailFastCheckerExceptionsContainer,
                )
            )

        if serializer is not None:
            plugins.append(generic_registration_plugin(serializer, Serializer))
        if message_body_serializer is not None:
            plugins.append(generic_registration_plugin(message_body_serializer, MessageBodySerializer))
        if message_body_serializer is not None:
            plugins.append(generic_registration_plugin(message_body_serializer, MessageHeadersSerializer))
        if idempotency is not None:
            plugins.append(IdempotencyPlugin(idempotency))

        if saga is not None and saga is not Empty:
            plugins.append(SagaPlugin(saga))  # type: ignore[arg-type]
        elif saga is not Empty:
            plugins.append(SagaPlugin(SagaConfig(storage=InMemorySagaStorage())))

        if default_router_registration:
            plugins.append(DefaultRouterRegistrationPlugin(default_router_registration))

        if isinstance(autosubscribe, AutosubscribeConfig):
            autosubscribe_plugin = autosubscribe.plugin
            plugins.append(autosubscribe_plugin)
        elif autosubscribe is not Empty and self.configurator.is_registered(SubscriptionStorage):
            plugins.append(AutosubscribeConfig().plugin)

        if unit_of_work is not None:
            plugins.append(UnitOfWorkPlugin(unit_of_work))

        if outbox is not None:
            plugins.append(OutboxPlugin(outbox))
        if message_id_generator is not None:
            plugins.append(generic_registration_plugin(message_id_generator, MessageIdGenerator))

        self.on_startup_hooks = list(on_startup_hooks or [])
        self.on_shutdown_hooks = list(on_shutdown_hooks or [])

        self.handler_activator.app = self
        self.configurator.mersal = self
        plugins.append(DefaultPlugin(pdb_on_exception=bool(pdb_on_exception)))
        for plugin in plugins:
            plugin(self.configurator)

        lifespan_handler = self.configurator.get(LifespanHandler)  # type: ignore[type-abstract]
        self.on_startup_hooks.extend(lifespan_handler.on_startup_hooks)
        self.on_shutdown_hooks.extend(lifespan_handler.on_shutdown_hooks)

        self.configurator.resolve()
        self.router = self.configurator.get(Router)  # type: ignore[type-abstract]
        self.logger = logging.getLogger("mersal")
        self.transport = self.configurator.get(Transport)  # type: ignore[type-abstract]
        self.worker_factory = self.configurator.get(WorkerFactory)  # type: ignore[type-abstract]
        self.worker_factory.app = self
        self.subscription_storage = self.configurator.get(SubscriptionStorage)  # type: ignore[type-abstract]
        self.topic_name_convention = self.configurator.get(TopicNameConvention)  # type: ignore[type-abstract]
        self.pipeline_invoker = self.configurator.get(PipelineInvoker)  # type: ignore[type-abstract]
        self.worker: Worker
        self._create_worker()
        self._exit_stack: AsyncExitStack | None = None

    async def start(self) -> None:
        for hook in self.on_startup_hooks:
            await AsyncCallable(hook)()
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.enter_async_context(self.worker)

    async def stop(self) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()

        self._exit_stack = None
        for hook in self.on_shutdown_hooks:
            await AsyncCallable(hook)()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        await self.stop()

    async def send(
        self,
        command_message: Any,
        headers: Mapping[str, Any] | None = None,
    ) -> None:
        logical_message = self._create_message(command_message, headers)

        destination_address = await self.router.get_destination_address(logical_message)
        self.logger.info(
            "The app named '%r' is about to send %r to %r",
            self.name,
            type(command_message),
            destination_address,
        )
        addresses = [destination_address]
        await self._send(set(addresses), logical_message)

    async def send_local(
        self,
        command_message: Any,
        headers: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger.info(
            "The app named '%r' is about to send %r locally",
            self.name,
            type(command_message),
        )

        destination_address = self.transport.address
        logical_message = self._create_message(command_message, headers)

        addresses = [destination_address]
        await self._send(set(addresses), logical_message)

    async def publish(self, event_message: Any, headers: Mapping[str, Any] | None = None) -> None:
        topic = self.topic_name_convention.get_topic_name(type(event_message))

        await self._inner_publish(topic, event_message, headers)

    async def subscribe(self, event_type: type) -> None:
        topic = self.topic_name_convention.get_topic_name(event_type)
        await self._subscribe(topic)

    async def _send(
        self,
        destination_addresses: set[str],
        logical_message: LogicalMessage,
    ) -> None:
        transaction_context = self._get_transaction_context()

        if not transaction_context:
            async with DefaultTransactionContextWithOwningApp(self) as transaction_context:
                await self._invoke_send(destination_addresses, logical_message, transaction_context)
                transaction_context.set_result(commit=True, ack=True)
                try:
                    await transaction_context.complete()
                except:  # noqa: E722
                    self.logger.exception(
                        "Exception while trying to complete the transaction context when sending %r",
                        logical_message.message_label,
                    )
        else:
            await self._invoke_send(destination_addresses, logical_message, transaction_context)

    def _get_transaction_context(self) -> TransactionContext | None:
        ambient_transaction_context = AmbientContext().current

        if not ambient_transaction_context:
            return None

        if (
            not isinstance(ambient_transaction_context, DefaultTransactionContextWithOwningApp)
            or ambient_transaction_context.app is not self
        ):
            return None

        return ambient_transaction_context

    async def _invoke_send(
        self,
        destination_addresses: set[str],
        logical_message: LogicalMessage,
        transaction_context: TransactionContext,
    ) -> None:
        self.logger.info(
            "The app named '%r' is about to send %r with id: %r to destination addresses %r",
            self.name,
            str(type(logical_message.body)),
            str(logical_message.headers.get("message_id", "N/A")),
            str(destination_addresses),
        )
        context = OutgoingStepContext(
            logical_message,
            transaction_context,
            DestinationAddresses(destination_addresses),
        )
        await self.pipeline_invoker(context)

    async def _inner_publish(self, topic: str, event_message: Any, headers: Mapping[str, Any] | None) -> None:
        message = self._create_message(event_message, headers)
        subscriber_addresses = await self.subscription_storage.get_subscriber_addresses(topic)
        await self._send(subscriber_addresses, message)

    async def _subscribe(self, topic: str) -> None:
        subscriber_address = self.transport.address
        if self.subscription_storage.is_centralized:
            await self.subscription_storage.register_subscriber(topic, subscriber_address)
        else:
            raise NotImplementedError("Can't handle transports that handle pub/sub natively yet")

    def _create_message(self, body: Any, headers: Mapping[str, Any] | None) -> LogicalMessage:
        _headers = MessageHeaders(headers) if headers else MessageHeaders()

        return LogicalMessage(body, _headers)

    def _create_worker(self) -> None:
        self.logger.info("The app named '%r' is creating a worker", self.name)
        self.worker = self.worker_factory.create_worker(self.name)
