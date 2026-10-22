"""Readiness checks: each check is an async callable that returns on success and raises when its dependency is down."""

import asyncio
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

Check = Callable[[], Awaitable[None]]


def postgres_check(engine: AsyncEngine) -> Check:
    async def check() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    return check


def redis_check(client: Redis) -> Check:
    async def check() -> None:
        await client.ping()

    return check


async def run_checks(checks: dict[str, Check], timeout: float) -> dict[str, str]:
    """Run every check concurrently; a check that raises or exceeds the timeout is "down"."""

    async def one(check: Check) -> str:
        try:
            await asyncio.wait_for(check(), timeout)
        except Exception:
            # The error text can hold hosts or credentials, so it never leaves this function.
            return "down"
        return "ok"

    results = await asyncio.gather(*(one(c) for c in checks.values()))
    return dict(zip(checks, results, strict=True))
