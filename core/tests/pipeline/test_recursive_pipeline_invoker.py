from collections.abc import Callable

import pytest

from mersal.pipeline import (
    RecursivePipelineInvoker,
)
from mersal.pipeline.pipeline import IncomingPipeline, OutgoingPipeline
from mersal.pipeline.pipeline_invoker import PipelineInvoker
from mersal_testing.pipeline.pipeline_invoker_tests import (
    PipelineInvokerTestsBase,
)

__all__ = ("TestRecursivePipelineInvoker",)


pytestmark = pytest.mark.anyio


class TestRecursivePipelineInvoker(PipelineInvokerTestsBase):
    @pytest.fixture
    def pipeline_invoker_maker(self) -> Callable[..., PipelineInvoker]:
        def maker(
            *,
            incoming_pipeline: IncomingPipeline,
            outgoing_pipeline: OutgoingPipeline,
            **kwargs,
        ) -> PipelineInvoker:
            return RecursivePipelineInvoker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)

        return maker
