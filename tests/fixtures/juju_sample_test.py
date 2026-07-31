import asyncio

import juju

seen = []


@juju.test
async def first_test():
    await asyncio.sleep(0.01)
    seen.append("first")


@juju.test
async def second_test():
    seen.append("second")
    assert len(seen) >= 1
