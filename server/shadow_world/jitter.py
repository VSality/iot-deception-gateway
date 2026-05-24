import asyncio
import random

JITTER_MIN_SECONDS = 0.1
JITTER_MAX_SECONDS = 0.3


async def apply_shadow_jitter() -> None:
    await asyncio.sleep(random.uniform(JITTER_MIN_SECONDS, JITTER_MAX_SECONDS))


STATES_JITTER_MIN_SECONDS = 0.15
STATES_JITTER_MAX_SECONDS = 0.35


async def apply_states_jitter() -> None:
    await asyncio.sleep(
        random.uniform(STATES_JITTER_MIN_SECONDS, STATES_JITTER_MAX_SECONDS)
    )
