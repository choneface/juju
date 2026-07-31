import asyncio

import be_the_cowboy

seen = []


@be_the_cowboy.test
async def first_test():
    await asyncio.sleep(0.01)
    seen.append("first")


@be_the_cowboy.test
async def second_test():
    seen.append("second")
    assert len(seen) >= 1
