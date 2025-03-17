import uuid

from mersal.retry import DefaultFailFastChecker

__all__ = (
    "MyCustomException",
    "TestDefaultFailFastChecker",
)


class MyCustomException(Exception):
    pass


class TestDefaultFailFastChecker:
    def test_fails_when_finding_a_fail_fast_exception_type(self):
        fail_fast_exceptions = [MyCustomException, ValueError]
        subject = DefaultFailFastChecker(fail_fast_exceptions)
        result = subject.should_fail_fast(uuid.uuid4(), MyCustomException())
        assert result

    def test_should_not_fail_when_not_finding_a_fail_fast_exception_type(self):
        fail_fast_exceptions = [MyCustomException, ValueError]
        subject = DefaultFailFastChecker(fail_fast_exceptions)
        result = subject.should_fail_fast(uuid.uuid4(), Exception())
        assert not result
