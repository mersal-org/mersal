import pytest

from mersal.pipeline import IncomingStepContext
from mersal.transport.transaction_scope import TransactionScope
from mersal.types import Factory
from mersal.unit_of_work import UnitOfWorkConfig
from mersal.unit_of_work.unit_of_work_step import UnitOfWorkStep
from mersal_testing.counter import Counter, FailingCounter
from mersal_testing.test_doubles import (
    TransportMessageBuilder,
    UnitOfWorkTestHelper,
)

__all__ = ("TestUnitOfWorkStep",)


pytestmark = pytest.mark.anyio


class TestUnitOfWorkStep:
    @pytest.fixture
    def subject_maker(self) -> Factory[UnitOfWorkStep]:
        def maker(config: UnitOfWorkConfig) -> UnitOfWorkStep:
            return UnitOfWorkStep(config)

        return maker

    @pytest.fixture
    def subject(self, uow_config: UnitOfWorkConfig, subject_maker: Factory[UnitOfWorkStep]) -> UnitOfWorkStep:
        return subject_maker(uow_config)

    @pytest.fixture
    def uow_helper(self) -> UnitOfWorkTestHelper:
        return UnitOfWorkTestHelper()

    @pytest.fixture
    def uow_commit_with_transaction(self) -> bool:
        return False

    @pytest.fixture
    def uow_config(self, uow_helper: UnitOfWorkTestHelper, uow_commit_with_transaction: bool) -> UnitOfWorkConfig:
        return UnitOfWorkConfig(
            uow_factory=uow_helper.uow_factory,
            commit_action=uow_helper.commit_action,
            rollback_action=uow_helper.rollback_action,
            close_action=uow_helper.close_action,
            commit_with_transaction=uow_commit_with_transaction,
        )

    async def test_rollback_on_failure(self, subject: UnitOfWorkStep, uow_helper: UnitOfWorkTestHelper):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            counter = FailingCounter([1])
            transport_message = TransportMessageBuilder.build()
            context = IncomingStepContext(transport_message, transaction_context)
            with pytest.raises(Exception):
                await subject(context, counter.task)

            assert uow_helper.rollbacked == 1
            assert uow_helper.committed == 0
            assert uow_helper.closed == 1

    async def test_committing_if_next_step_does_not_throw(
        self, subject: UnitOfWorkStep, uow_helper: UnitOfWorkTestHelper
    ):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            counter = Counter()
            transport_message = TransportMessageBuilder.build()
            context = IncomingStepContext(transport_message, transaction_context)
            await subject(context, counter.task)

            assert uow_helper.rollbacked == 0
            assert uow_helper.committed == 1
            assert uow_helper.closed == 1

            assert counter.total == 1

    @pytest.mark.parametrize("uow_commit_with_transaction", [True])
    async def test_committing_as_part_of_transaction_completion(
        self,
        subject: UnitOfWorkStep,
        uow_helper: UnitOfWorkTestHelper,
    ):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            counter = Counter()
            transport_message = TransportMessageBuilder.build()
            context = IncomingStepContext(transport_message, transaction_context)
            await subject(context, counter.task)
            assert uow_helper.rollbacked == 0
            assert uow_helper.committed == 0
            assert uow_helper.closed == 0
            transaction_context.set_result(True, True)
            await transaction_context.complete()
            assert uow_helper.rollbacked == 0
            assert uow_helper.committed == 1
            assert uow_helper.closed == 0
            await transaction_context.close()
            assert uow_helper.closed == 1

            assert counter.total == 1

    @pytest.mark.parametrize("uow_commit_with_transaction", [True])
    async def test_rollback_as_part_of_transaction_completion(
        self, subject: UnitOfWorkStep, uow_helper: UnitOfWorkTestHelper
    ):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            counter = FailingCounter([1])
            transport_message = TransportMessageBuilder.build()
            context = IncomingStepContext(transport_message, transaction_context)
            with pytest.raises(Exception):
                await subject(context, counter.task)
            assert uow_helper.rollbacked == 0
            assert uow_helper.committed == 0
            assert uow_helper.closed == 0
            transaction_context.set_result(False, True)
            await transaction_context.complete()
            assert uow_helper.rollbacked == 1
            assert uow_helper.committed == 0
            assert uow_helper.closed == 0
            await transaction_context.close()
            assert uow_helper.closed == 1

            assert counter.calls == 1
