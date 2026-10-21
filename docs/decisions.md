# Decisions
Why the project is built the way it is. One entry per decision, newest last. A changed decision gets a new entry, never an edit.

## 2026-10-21 D-001: /ops/ready checks Postgres and Redis
- Decision: GET /ops/ready answers 200 only when both Postgres and Redis respond, otherwise 503 naming the one that is down.
- Why: the app needs both from week 2; a missing dependency shows up in seconds instead of as confusing errors later.
- Not chosen: Postgres only - Redis outages would go unnoticed; no checks yet - readiness would mean nothing.
- Affects: api/routers/ops.py, core/health.py, tests/test_ops.py
- Context: T-001

## 2026-10-21 D-002: Libraries listed in pyproject.toml
- Decision: runtime fastapi, uvicorn, sqlalchemy, asyncpg, redis, pydantic-settings; dev pytest, httpx, ruff, pyyaml; all in one pyproject.toml, installed with `pip install -e .[dev]`.
- Why: one modern file for dependencies and tool settings (ruff, pytest).
- Not chosen: requirements.txt + requirements-dev.txt (System 1 style) - two files, tool config elsewhere.
- Affects: pyproject.toml, Dockerfile, .github/workflows/ci.yml, README.md
- Context: T-001

## 2026-10-21 D-003: CI uses actions/checkout@v5 and actions/setup-python@v6
- Decision: bump both actions to the versions that run on Node.js 24.
- Why: v4/v5 target the deprecated Node.js 20 and GitHub warned on every run.
- Not chosen: keep v4/v5 - warnings now, breakage when Node.js 20 is removed.
- Affects: .github/workflows/ci.yml
- Context: T-001

## 2026-10-21 D-004: Compose ports bound to 127.0.0.1
- Decision: every service in infra/docker-compose.yml publishes its port on 127.0.0.1 only.
- Why: Redis has no password; nothing in the local stack should be reachable from the network (risk review LOW 1).
- Not chosen: 0.0.0.0 (Docker default) - anyone on the same wifi could reach Redis and Postgres.
- Affects: infra/docker-compose.yml, tests/test_compose.py
- Context: T-001

## 2026-10-21 D-005: Database URL built from separate settings
- Decision: Settings builds the URL from POSTGRES_USER, _PASSWORD, _HOST, _PORT and _DB with SQLAlchemy URL.create, which encodes the password; a non-empty DATABASE_URL still wins.
- Why: a password with @ / : # ? broke the hand-built URL and made /ops/ready report Postgres down (risk review LOW 2).
- Not chosen: require a URL-safe password - a rule people forget.
- Affects: core/config.py, api/main.py, infra/docker-compose.yml, .env.example, tests/test_config.py
- Context: T-001

## 2026-10-21 D-006: Remaining low review findings left for later
- Decision: unpinned versions and image tags, public /ops/ready load and default Postgres names stay open, listed in PR #1 and the handoff.
- Why: none blocks a local skeleton; each is small and fits its own task.
- Not chosen: fix them in T-001 - grows the task past its contract.
- Affects: PR #1 description, docs/progress.md open questions
- Context: T-001
