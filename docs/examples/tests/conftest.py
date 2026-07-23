import pytest

__all__ = ("anyio_backend",)


@pytest.fixture(params=[pytest.param("asyncio", id="asyncio")])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    # SQLAlchemy's async engine doesn't support trio, same restriction as
    # testing/mersal_testing/_internal/conftest.py
    return str(request.param)
