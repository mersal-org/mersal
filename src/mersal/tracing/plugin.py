from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.pipeline import PipelineInjectionPosition, PipelineInjector
from mersal.pipeline.pipeline import IncomingPipeline, OutgoingPipeline
from mersal.pipeline.send.serialize_outgoing_message_step import SerializeOutgoingMessageStep
from mersal.plugins import Plugin
from mersal.tracing.trace_context_steps import TraceContextIncomingStep, TraceContextOutgoingStep

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator

__all__ = ("TracingPlugin",)


class TracingPlugin(Plugin):
    """Propagates the W3C trace context across the bus: every outgoing message
    carries the current trace as a `traceparent` header, and receiving a message
    makes its trace the current one (see `mersal.tracing.current_trace_context`)
    for the rest of its pipeline. With logging enabled, the received message's
    `trace_id`/`span_id`/`trace_sampled` are also bound onto its `LogContext`.

    Propagation only - no spans are recorded or exported. A future OpenTelemetry
    integration replaces this plugin rather than running alongside it, so that
    there's one source of the current trace.
    """

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_incoming_pipeline(configurator: StandardConfigurator) -> PipelineInjector:
            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            # First, so retries, deferral handling and the handlers themselves
            # all run under the message's trace.
            pipeline.prepend_step(TraceContextIncomingStep())
            return pipeline

        def decorate_outgoing_pipeline(configurator: StandardConfigurator) -> PipelineInjector:
            pipeline = PipelineInjector(configurator.get(OutgoingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(
                TraceContextOutgoingStep(),
                PipelineInjectionPosition.BEFORE,
                SerializeOutgoingMessageStep,
            )
            return pipeline

        configurator.decorate(IncomingPipeline, decorate_incoming_pipeline)
        configurator.decorate(OutgoingPipeline, decorate_outgoing_pipeline)
