# Decisions

## D-001: Dependencies in pyproject.toml
- Date: 2026-10-21 · Task: T-001 · Decided by: user
- Decision: one pyproject.toml for dependencies and tool config (ruff, pytest); install with `pip install -e .[dev]`.
- Why: one modern file instead of several.
- Rejected: requirements.txt + requirements-dev.txt (System 1 style).

## D-002: Local ports bound to 127.0.0.1
- Date: 2026-10-21 · Task: T-001 · Decided by: user
- Decision: every Compose port publishes on 127.0.0.1.
- Why: Redis has no password; nothing should be reachable from the network (risk review LOW 1).
- Rejected: 0.0.0.0 (Docker default).

## D-003: Database URL built from separate settings
- Date: 2026-10-21 · Task: T-001 · Decided by: user (fix it); approach proposed by Claude
- Decision: Settings builds the database URL from POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT and POSTGRES_DB with SQLAlchemy `URL.create`, which encodes the password; an explicit non-empty DATABASE_URL still wins.
- Why: a password with `@ / : # ?` broke the hand-built URL and made /ops/ready report Postgres down (risk review LOW 2).
- Rejected: requiring a URL-safe password (a rule people forget).
