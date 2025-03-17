import enum
from collections import defaultdict
from collections.abc import MutableSequence, Sequence
from typing import TypeAlias, TypeVar

from .incoming_step import IncomingStep
from .outgoing_step import OutgoingStep
from .pipeline import Pipeline

__all__ = (
    "PipelineInjectionPosition",
    "PipelineInjector",
)


class PipelineInjectionPosition(enum.Enum):
    AFTER = "AFTER"
    BEFORE = "BEFORE"


StepType = TypeVar("StepType", bound=IncomingStep | OutgoingStep)
Step: TypeAlias = IncomingStep | OutgoingStep


class PipelineInjector(Pipeline):
    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline
        self.__prepend: MutableSequence[IncomingStep] = []
        self._append: MutableSequence[IncomingStep] = []
        self.__inject: dict[type[Step], list[tuple[PipelineInjectionPosition, Step]]] = defaultdict(list)

    def __call__(self) -> Sequence[Step]:
        steps = [
            *self.__prepend,
            *self.pipeline(),
            *self._append,
        ]
        results: MutableSequence[Step] = []
        for step in steps:
            injections = self.__inject.get(type(step), [])
            self._extract_injections_and_add_to_results(step, injections, results)
        return results

    def prepend_step(self, step: IncomingStep) -> None:
        self.__prepend.insert(0, step)

    def append_step(self, step: IncomingStep) -> None:
        self._append.append(step)

    def inject_step(
        self,
        step: Step,
        position: PipelineInjectionPosition,
        relative_to: type[Step],
    ) -> None:
        self.__inject[relative_to].append((position, step))

    def _extract_injections_and_add_to_results(
        self,
        step: Step,
        injections: list[tuple[PipelineInjectionPosition, Step]],
        results: MutableSequence[Step],
    ) -> None:
        before_steps = [x for x in injections if x[0] is PipelineInjectionPosition.BEFORE]
        results.extend([x[1] for x in before_steps])
        results.append(step)
        after_steps = [x for x in injections if x[0] is PipelineInjectionPosition.AFTER]
        results.extend([x[1] for x in after_steps])
