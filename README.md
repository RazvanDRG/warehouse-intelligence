# warehouse-intelligence

AI system that attaches to the Warehouse Operations Service (System 1). Work in progress: this is the week 1 skeleton.

## Layout

- `core/`: generic parts (search, LLM gateway, cache, agent, MCP, Quality Lab, observability). Never imports `adapters/`.
- `adapters/warehouse/`: everything specific to System 1.
- `api/`: FastAPI routers.
- `pipelines/`: background jobs.
- `infra/`: Docker Compose, Prometheus and Grafana config.

## Run locally

```sh
cp .env.example .env          # then fill in the passwords
docker compose --env-file .env -f infra/docker-compose.yml up -d
curl localhost:8001/ops/ready # 200 when Postgres and Redis answer
```

Ports avoid System 1 (5432, 8000): API 8001, Postgres 5433, Redis 6379, Prometheus 9090, Grafana 3000.

## Check

```sh
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # bin/ instead of Scripts/ on Linux and macOS
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m pytest -q && .venv/Scripts/python tools/boundary_check.py
```

## Limits

- `/ops/live` and `/ops/ready` are public, with no auth, like System 1's health ping. `/metrics` (admin) is not built yet, so Prometheus scrapes only itself.
- No database tables or migrations yet.
