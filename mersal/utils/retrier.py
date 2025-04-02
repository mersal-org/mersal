from anyio import sleep

from mersal.types import AsyncAnyCallable

__all__ = ("AsyncRetrier",)


class AsyncRetrier:
    def __init__(self, delays: list[float]):
        self.delays = delays

    async def run(self, func: AsyncAnyCallable) -> None:
        retry_number = 0
        max_no_of_retries = len(self.delays)
        while retry_number <= max_no_of_retries:
            try:
                await func()
                return
            except Exception:
                if retry_number == max_no_of_retries:
                    raise
                delay = self.delays[retry_number]
                await sleep(delay)
            retry_number += 1
