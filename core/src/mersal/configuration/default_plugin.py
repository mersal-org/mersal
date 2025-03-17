from mersal.activation import HandlerActivator
from mersal.configuration.standard_configurator import (
    StandardConfigurator,
    StandardConfiguratorResolver,
)
from mersal.lifespan import DefaultLifespanHandler, LifespanHandler
from mersal.persistence.not_implemented import NotImplementedSubscriptionStorage
from mersal.pipeline import (
    ActivateHandlersStep,
    DefaultIncomingPipeline,
    DefaultOutgoingPipeline,
    DeserializeIncomingMessageStep,
    DispatchIncomingMessageStep,
    FlowCorrelationStep,
    IncomingPipeline,
    MessageIdGenerator,
    OutgoingPipeline,
    PipelineInvoker,
    RecursivePipelineInvoker,
    SendOutgoingMessageStep,
    SerializeOutgoingMessageStep,
    SetDefaultHeadersStep,
)
from mersal.plugins import Plugin
from mersal.retry import (
    DeadletterQueueErrorHandler,
    DefaultFailFastChecker,
    DefaultRetryStrategy,
    ErrorHandler,
    ErrorTracker,
    FailFastChecker,
    InMemoryErrorTracker,
    RetryStep,
    RetryStrategy,
    RetryStrategySettings,
)
from mersal.retry.fail_fast.default_fail_fast_checker import (
    DefaultFailFastCheckerExceptionsContainer,
)
from mersal.routing import Router
from mersal.routing.default import DefaultRouter
from mersal.serialization import (
    MessageBodySerializer,
    MessageHeadersSerializer,
    MessageSerializer,
    Serializer,
)
from mersal.subscription import SubscriptionStorage
from mersal.topic import DefaultTopicNameConvention, TopicNameConvention
from mersal.transport import Transport
from mersal.workers import WorkerFactory
from mersal.workers.anyio import AnyioWorkerFactory

__all__ = ("DefaultPlugin",)


class DefaultPlugin(Plugin):
    def __init__(self, pdb_on_exception: bool) -> None:
        self.pdb_on_exception = pdb_on_exception

    def __call__(self, configurator: StandardConfigurator) -> None:
        self.configurator = configurator

        self._register_default_dependency_if_needed(RetryStrategySettings, lambda _: RetryStrategySettings())
        self._register_default_dependency_if_needed(SubscriptionStorage, lambda _: NotImplementedSubscriptionStorage())
        self._register_default_dependency_if_needed(
            ErrorTracker,
            lambda d: InMemoryErrorTracker(d.get(RetryStrategySettings).max_no_of_retries),
        )

        self._register_default_dependency_if_needed(
            ErrorHandler,
            lambda config: DeadletterQueueErrorHandler(
                transport=config.get(Transport),  # type: ignore[type-abstract]
                error_queue_name=config.get(RetryStrategySettings).error_queue_name,
            ),
        )
        self._register_default_dependency_if_needed(
            DefaultFailFastCheckerExceptionsContainer,
            lambda _: DefaultFailFastCheckerExceptionsContainer([]),
        )
        self._register_default_dependency_if_needed(
            FailFastChecker,
            lambda config: DefaultFailFastChecker(
                fail_fast_exceptions=config.get(DefaultFailFastCheckerExceptionsContainer).exceptions
            ),
        )
        self._register_default_dependency_if_needed(Router, lambda _: DefaultRouter())
        self._register_default_dependency_if_needed(
            RetryStrategy,
            lambda config: DefaultRetryStrategy(
                error_tracker=config.get(ErrorTracker),  # type: ignore[type-abstract]
                error_handler=config.get(ErrorHandler),  # type: ignore[type-abstract]
                fail_fast_checker=config.get(FailFastChecker),  # type: ignore[type-abstract]
                pdb_on_exception=self.pdb_on_exception,
            ),
        )
        self._register_default_dependency_if_needed(
            RetryStep,
            lambda config: config.get(RetryStrategy).get_retry_step(),  # type: ignore[type-abstract]
        )
        self._register_default_dependency_if_needed(LifespanHandler, lambda _: DefaultLifespanHandler())

        self._register_default_dependency_if_needed(MessageBodySerializer, lambda config: config.get(Serializer))  # type: ignore[type-abstract]
        self._register_default_dependency_if_needed(MessageHeadersSerializer, lambda config: config.get(Serializer))  # type: ignore[type-abstract]

        def register_default_message_serializer(
            config: StandardConfigurator,
        ) -> MessageSerializer:
            serializer = config.get(MessageBodySerializer)  # type: ignore[type-abstract]

            return MessageSerializer(serializer)

        self._register_default_dependency_if_needed(MessageSerializer, register_default_message_serializer)

        def register_default_incoming_pipeline(
            config: StandardConfigurator,
        ) -> IncomingPipeline:
            return (
                DefaultIncomingPipeline()
                .append(config.get(RetryStep))  # type: ignore[type-abstract]
                .append(DeserializeIncomingMessageStep(config.get(MessageSerializer)))
                .append(ActivateHandlersStep(config.get(HandlerActivator)))  # type: ignore[type-abstract]
                .append(DispatchIncomingMessageStep())
            )

        self._register_default_dependency_if_needed(IncomingPipeline, register_default_incoming_pipeline)

        def register_default_outgoing_pipeline(
            config: StandardConfigurator,
        ) -> OutgoingPipeline:
            return (
                DefaultOutgoingPipeline()
                .append(SetDefaultHeadersStep(message_id_generator=config.get_optional(MessageIdGenerator)))  # type: ignore[type-abstract]
                .append(FlowCorrelationStep())
                .append(SerializeOutgoingMessageStep(config.get(MessageSerializer)))
                .append(SendOutgoingMessageStep(config.get(Transport)))  # type: ignore[type-abstract]
            )

        self._register_default_dependency_if_needed(OutgoingPipeline, register_default_outgoing_pipeline)

        self._register_default_dependency_if_needed(
            PipelineInvoker,
            lambda config: RecursivePipelineInvoker(config.get(IncomingPipeline), config.get(OutgoingPipeline)),  # type: ignore[type-abstract]
        )

        self._register_default_dependency_if_needed(TopicNameConvention, lambda _: DefaultTopicNameConvention())

        self._register_default_dependency_if_needed(
            WorkerFactory,
            lambda config: AnyioWorkerFactory(
                transport=config.get(Transport),  # type: ignore[type-abstract]
                pipeline_invoker=config.get(PipelineInvoker),  # type: ignore[type-abstract]
            ),
        )

    def _register_default_dependency_if_needed(
        self, dependency_type: type, resolver: StandardConfiguratorResolver
    ) -> None:
        if not self.configurator.is_registered(dependency_type):
            self.configurator.register(dependency_type, resolver)
