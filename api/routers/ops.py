from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.health import Check, run_checks

router = APIRouter(prefix="/ops", tags=["ops"])


def get_readiness_checks(request: Request) -> dict[str, Check]:
    return request.app.state.readiness_checks


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request, checks: Annotated[dict[str, Check], Depends(get_readiness_checks)]) -> JSONResponse:
    results = await run_checks(checks, request.app.state.settings.readiness_timeout_seconds)
    is_ready = all(status == "ok" for status in results.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": results},
    )
