from fastapi.testclient import TestClient

from api.main import create_app
from api.routers.ops import get_readiness_checks


async def ok() -> None:
    return None


async def down() -> None:
    raise ConnectionError("connection refused")


def client_with(checks: dict) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_readiness_checks] = lambda: checks
    return TestClient(app)


def test_live_ok():
    # No overrides and no lifespan: live must answer without any dependency.
    response = TestClient(create_app()).get("/ops/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok():
    response = client_with({"postgres": ok, "redis": ok}).get("/ops/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"postgres": "ok", "redis": "ok"}}


def test_ready_postgres_down():
    response = client_with({"postgres": down, "redis": ok}).get("/ops/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"postgres": "down", "redis": "ok"}}


def test_ready_redis_down():
    response = client_with({"postgres": ok, "redis": down}).get("/ops/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"postgres": "ok", "redis": "down"}}


def test_ready_does_not_leak_error_text():
    response = client_with({"postgres": down, "redis": ok}).get("/ops/ready")
    assert "connection refused" not in response.text
