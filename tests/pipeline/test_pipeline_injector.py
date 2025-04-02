from mersal.pipeline import (
    DefaultIncomingPipeline,
    IncomingStepContext,
    OutgoingStepContext,
    PipelineInjectionPosition,
    PipelineInjector,
)
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.outgoing_step import OutgoingStep
from mersal.types import AsyncAnyCallable

__all__ = (
    "DummyIncomingStep",
    "DummyOutgoingStep",
    "SecondDummyIncomingStep",
    "SecondDummyOutgoingStep",
    "TestPipelineInjector",
    "ThirdDummyIncomingStep",
    "ThirdDummyOutgoingStep",
)


class DummyIncomingStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable):
        pass


class SecondDummyIncomingStep(DummyIncomingStep):
    pass


class ThirdDummyIncomingStep(DummyIncomingStep):
    pass


class DummyOutgoingStep(OutgoingStep):
    async def __call__(self, context: OutgoingStepContext, next_step: AsyncAnyCallable):
        pass


class SecondDummyOutgoingStep(DummyOutgoingStep):
    pass


class ThirdDummyOutgoingStep(DummyOutgoingStep):
    pass


class TestPipelineInjector:
    def test_injects_at_the_beginning(self):
        pipeline = DefaultIncomingPipeline()
        step1 = DummyIncomingStep()
        step2 = DummyIncomingStep()
        pipeline.append_step(step1)
        pipeline.append_step(step2)

        subject = PipelineInjector(pipeline)

        prepend_step = DummyIncomingStep()
        prepend_step2 = DummyIncomingStep()
        subject.prepend_step(prepend_step)
        subject.prepend_step(prepend_step2)

        assert subject() == [
            prepend_step2,
            prepend_step,
            step1,
            step2,
        ]

    def test_injects_at_the_end(self):
        pipeline = DefaultIncomingPipeline()
        step1 = DummyIncomingStep()
        step2 = DummyIncomingStep()
        pipeline.append_step(step1)
        pipeline.append_step(step2)

        subject = PipelineInjector(pipeline)

        append_step = DummyIncomingStep()
        append_step2 = DummyIncomingStep()
        subject.append_step(append_step)
        subject.append_step(append_step2)

        assert subject() == [
            step1,
            step2,
            append_step,
            append_step2,
        ]

    def test_injects_at_relative_position(self):
        pipeline = DefaultIncomingPipeline()
        step1 = DummyIncomingStep()
        step2 = SecondDummyIncomingStep()
        pipeline.append_step(step1)
        pipeline.append_step(step2)

        subject = PipelineInjector(pipeline)

        third_step = ThirdDummyIncomingStep()
        subject.inject_step(third_step, PipelineInjectionPosition.BEFORE, type(step1))
        subject.inject_step(third_step, PipelineInjectionPosition.AFTER, type(step2))
        subject.inject_step(third_step, PipelineInjectionPosition.AFTER, type(step1))

        assert subject() == [
            third_step,
            step1,
            third_step,
            step2,
            third_step,
        ]
