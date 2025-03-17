from collections.abc import Callable

import pytest

from mersal.pipeline import (
    IterativePipelineInvoker,
)
from mersal.pipeline.pipeline import IncomingPipeline, OutgoingPipeline
from mersal.pipeline.pipeline_invoker import PipelineInvoker
from mersal_testing.pipeline.pipeline_invoker_tests import (
    PipelineInvokerTestsBase,
)

__all__ = ("TestIterativePipelineInvoker",)


pytestmark = pytest.mark.anyio


class TestIterativePipelineInvoker(PipelineInvokerTestsBase):
    @pytest.fixture
    def pipeline_invoker_maker(self) -> Callable[..., PipelineInvoker]:
        def maker(
            *, incoming_pipeline: IncomingPipeline, outgoing_pipeline: OutgoingPipeline, **kwargs
        ) -> PipelineInvoker:
            return IterativePipelineInvoker(incoming_pipeline=incoming_pipeline, outgoing_pipeline=outgoing_pipeline)

        return maker
