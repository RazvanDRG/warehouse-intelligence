# Warehouse Intelligence

An AI layer that attaches to the Warehouse Operations Service (System 1) and makes it easier to understand, operate and debug. Not a chatbot on top of data: every answer will have a full trace, and its quality will be measured automatically.

The flow it is built for:
System 1 events → Kafka → index and projections → question or incident → answer with citations or a proposed action → human approval

**Status:** week 1 of 10. The repo skeleton is done: API with health checks, the local stack, tests and CI. The AI modules come next (see Future Improvements).

## 🌐 Live Demo

- Not deployed yet. Planned on free tiers (Render, Vercel, Supabase, Aiven) in week 10.

---

## ✅ Key Capabilities

- Liveness and readiness endpoints: the API reports whether Postgres and Redis answer, within a timeout
- The whole local stack starts with one command: API, Postgres with pgvector, Redis, Prometheus, Grafana
- Runs side by side with System 1 on the same machine (different ports)
- Every push is checked by CI: lint, format, tests, the one-door boundary check and a Docker build
- One door to System 1: only one adapter file may call it, checked in CI

---

## 🧱 Tech Stack

**Backend**
- Python 3.11, FastAPI, SQLAlchemy 2 (async) with asyncpg, Redis, pydantic-settings
- PostgreSQL 16 with pgvector (vector search inside Postgres)
- Docker (multi-stage image, non-root user) and Docker Compose
- Pytest (15 tests), Ruff (lint and format)
- GitHub Actions (CI)

**Observability**
- Prometheus and Grafana in the local stack

**Planned:** Kafka consumer (aiokafka), LLM gateway, LangChain, hybrid search, MCP, PyTorch and Transformers for an embeddings model

---

## 🚀 Features

### Built
- `GET /ops/live`: answers 200 without touching any dependency
- `GET /ops/ready`: checks Postgres and Redis at the same time, with a timeout; 200 when both answer, 503 naming the one that is down, and no error text that could expose hosts or passwords
- Local stack on 127.0.0.1 only, so nothing is reachable from the network
- Database settings passed as separate parts, so any password works

### Planned modules
- **A. Warehouse Map:** live digital twins of zones, racks and orders
- **B. Process Topology:** a graph of what each action in System 1 really does
- **C. RAG Copilot:** questions answered with hybrid search and citations, safe text-to-SQL
- **D. Incident Inbox + agent:** detects problems, proposes a fix, a human approves before anything changes
- **E. Vector Space Explorer:** a visual map of the knowledge base
- **F. Quality Lab:** simulator, golden set and automatic evaluation of the answers
- **G. GenAI features:** free-text orders, a daily warehouse report with verified numbers

---

## 🎯 Design Decisions

- `/ops/ready` checks both Postgres and Redis, so a missing dependency shows up in seconds instead of as confusing errors later (D-001)
- Libraries and tool settings live in one `pyproject.toml`, installed with `pip install -e ".[dev]"` (D-002)
- Every local port binds to 127.0.0.1: Redis has no password, so nothing should be reachable from the network (D-004)
- The database URL is built from separate settings, so a password with `@` or `:` cannot break it (D-005)
- `core/` never imports `adapters/`: the AI parts stay generic, everything specific to System 1 lives in one place
- System 1 is touched only through read channels (Kafka events, the schema, read endpoints) and one controlled write channel, used by the agent only after a human approves

Every decision, with the alternative not chosen: `docs/decisions.md`.

---

## 📊 Architecture Overview

```
System 1 ──Kafka events──► Warehouse Intelligence ──► answers with citations, incidents, proposals
   ▲                              │
   └── REST, only after a human approves an action (one adapter file)

Inside:  api/ (FastAPI routers) ─► core/ (generic: search, LLM gateway, agent, observability)
                                   adapters/warehouse/ (everything specific to System 1)
                                   pipelines/ (background jobs)
```

---

## 🧪 Running Locally

```sh
cp .env.example .env          # then set POSTGRES_PASSWORD and GRAFANA_ADMIN_PASSWORD to any local values
docker compose --env-file .env -f infra/docker-compose.yml up -d
curl localhost:8001/ops/ready # 200 when Postgres and Redis answer
docker compose --env-file .env -f infra/docker-compose.yml down
```

Ports avoid System 1 (5432, 8000): API 8001, Postgres 5433, Redis 6379, Prometheus 9090, Grafana 3000.

### Run tests
```sh
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # bin/ instead of Scripts/ on Linux and macOS
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m pytest -q && .venv/Scripts/python tools/boundary_check.py
```

---

## ⚙️ CI

GitHub Actions on every push and pull request: `ruff check`, `ruff format --check`, `pytest`, the boundary check, and a `docker build` of the image. No secrets and no LLM keys in CI.

---

## 📋 API Endpoints

| Method | Path | What it does | Who may call it |
|---|---|---|---|
| GET | `/ops/live` | The API process is up | Public |
| GET | `/ops/ready` | Postgres and Redis answer (200) or which one is down (503) | Public |

---

## 🧪 Testing Strategy

- 15 tests, run in CI on every push
- The readiness checks are tested with faked dependencies: no real Postgres or Redis needed
- A test makes sure `core/` never imports `adapters/`
- Tests read `docker-compose.yml` and check every port binds to 127.0.0.1 and avoids System 1's ports
- The database URL is tested with passwords that contain `@`, `:` and `/`

---

## 🧠 What This Project Demonstrates

- Building an AI system on top of a real, existing system, without changing it to fit
- Clean boundaries: generic AI core, one adapter, one door to the other system
- Production habits from day one: health checks, CI, a non-root image, nothing exposed by default
- Decisions written down with their reasons and the options not chosen

---

## ⚠️ Limits

- No AI features yet: this is the week 1 skeleton
- `/ops/live` and `/ops/ready` are public, with no auth, like System 1's health ping
- No database tables or migrations yet; `/metrics` is not built, so Prometheus scrapes only itself
- Library versions and image tags are not pinned yet

---

## 🔧 Future Improvements

- Week 2: Kafka ingestion and projections
- Week 3: digital twin and the warehouse map
- Week 4: process topology
- Week 5: indexing, hybrid search and the LLM gateway
- Week 6: copilot, router and safe text-to-SQL
- Week 7: incident inbox, agent and MCP
- Week 8: UMAP explorer and the Quality Lab simulator
- Week 9: evaluation, observability and security
- Week 10: deploy, demo
- Also: pin versions and image tags, protect `/ops/ready` before deploy, pass the Postgres user and database names to the API explicitly

---

## 👤 About

Built solo by **Razvan-Gabriel Dornea**, Backend Developer (Python/FastAPI), as the second project of a two-system warehouse platform, next to the Warehouse Operations Service.

- LinkedIn: [linkedin.com/in/razvan-gabriel-dornea-697579184](https://www.linkedin.com/in/razvan-gabriel-dornea-697579184/)
- GitHub: [@RazvanDRG](https://github.com/RazvanDRG)
