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

## 2026-11-21 D-007: Read-only commands skip the guard prompt
- Decision: .claude/guard.json allow_commands lets git diff / rev-parse / branch --show-current, gh run view / list and python -m pytest run without asking.
- Why: the 90-day guard audit showed these asks repeat and never change code, data or GitHub.
- Not chosen: allowing git push, add or commit, alembic upgrade or CLAUDE.md edits - the kit rules require asking for them.
- Affects: .claude/guard.json
- Context: /kit-doctor --audit

## 2026-11-21 D-008: aiokafka reads System 1 events
- Decision: aiokafka is a runtime dependency in pyproject.toml, used only behind the EventSource in adapters/warehouse/.
- Why: the plan names it; it is async like FastAPI and free.
- Not chosen: confluent-kafka - sync C client, harder to install on Windows and in the slim image.
- Affects: pyproject.toml, adapters/warehouse/
- Context: T-002

## 2026-11-21 D-009: EventSource and Event live in core/events.py
- Decision: the generic Event type and EventSource Protocol sit in core/events.py; the Kafka implementation sits in adapters/warehouse/.
- Why: architecture section 19, the core uses events without knowing they come from Kafka or System 1.
- Not chosen: the interface inside adapters/warehouse/ - core would have to import the adapter.
- Affects: core/events.py, adapters/warehouse/
- Context: T-002

## 2026-11-21 D-010: An unreadable message stops the consumer until dead-letter exists
- Decision: a message with broken JSON or a missing envelope field raises an error and is not committed.
- Why: nothing is lost silently; Week 2 Wed replaces this with the dead-letter table.
- Not chosen: log and skip - the message would be marked done and lost.
- Affects: adapters/warehouse/ consumer
- Context: T-002

## 2026-11-21 D-011: Kafka login defaults to SASL PLAIN, like System 1
- Decision: KAFKA_SASL_MECHANISM defaults to PLAIN, the mechanism System 1's producer uses on the same Aiven cluster (Backend/app/services/kafka_producer.py).
- Why: one Aiven setup for both systems; the password is still sent inside TLS (SASL_SSL).
- Not chosen: SCRAM-SHA-256 as default - would need SCRAM enabled for the WI principal; still selectable through the variable.
- Affects: adapters/warehouse/kafka_config.py
- Context: T-002

## 2026-11-21 D-012: KAFKA_GROUP_ID is required, with no default
- Decision: the consumer refuses to start without KAFKA_GROUP_ID; every deployment and local run sets its own group.
- Why: a shared default lets a local run on Aiven take messages from the deployed reader (T-002 risk review).
- Not chosen: a default such as warehouse-intelligence - easy to reuse by accident.
- Affects: adapters/warehouse/kafka_config.py, .env.example
- Context: T-002 review loop 1

## 2026-11-22 D-013: Alembic for WI's database migrations
- Decision: every WI schema change is an Alembic migration with a working downgrade, run against WI's own Postgres only.
- Why: the project rules require versioned schema changes; Alembic is the standard tool next to SQLAlchemy.
- Not chosen: tables created by code at startup - no history, no downgrade.
- Affects: alembic.ini, alembic/, pyproject.toml
- Context: T-003

## 2026-11-22 D-014: Event carries an optional typed position
- Decision: Event gets an optional `position` (topic, partition, offset), set by the event source.
- Why: processed_events stores where each event came from; a typed field is checked, a metadata key is not.
- Not chosen: keys inside Event.metadata - untyped and easy to misspell.
- Affects: core/events.py, adapters/warehouse/kafka_source.py
- Context: T-003

## 2026-11-22 D-015: Duplicate check as a generic wrapper around the handler
- Decision: core/idempotency.py wraps a handler that receives (event, connection); one transaction holds the processed_events insert and the handler's writes.
- Why: both are saved or neither, and the event source stays free of database code.
- Not chosen: the transaction inside KafkaEventSource - ties the reader to the database.
- Affects: core/idempotency.py, every future event handler
- Context: T-003

## 2026-11-22 D-016: Database tests use TEST_DATABASE_URL, skipped locally when unset
- Decision: database tests run on a separate wi_test database; unset locally they skip with a visible reason, in CI they must run.
- Why: the local check works without Docker, while CI still proves the database behavior.
- Not chosen: always required - every local run would need Docker up.
- Affects: tests/, .env.example
- Context: T-003

## 2026-11-22 D-017: CI runs a Postgres service
- Decision: GitHub Actions starts pgvector/pgvector:pg16 with a throwaway password for the test step.
- Why: the database tests must run on every push; the service is free and lives only during the run.
- Not chosen: no database in CI - the migration and duplicate tests would never run there.
- Affects: .github/workflows/ci.yml
- Context: T-003
