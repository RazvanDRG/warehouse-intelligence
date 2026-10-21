from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from api.routers import ops
from core.config import Settings
from core.health import postgres_check, redis_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Both clients connect lazily, so startup never fails because a dependency is down; /ops/ready reports it.
    engine = create_async_engine(app.state.settings.database_url, pool_pre_ping=True)
    redis = Redis.from_url(app.state.settings.redis_url)
    app.state.readiness_checks = {"postgres": postgres_check(engine), "redis": redis_check(redis)}
    yield
    await redis.aclose()
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Warehouse Intelligence", lifespan=lifespan)
    app.state.settings = settings or Settings()
    app.include_router(ops.router)
    return app


app = create_app()
