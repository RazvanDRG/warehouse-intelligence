"""Test database access: a local Postgres only, named *_test, from TEST_DATABASE_URL (D-016)."""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
# localhost for a developer machine, postgres for the compose or CI service.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "postgres"}


class _TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    test_database_url: str = ""


def check_test_database_url(url: str) -> str:
    """Refuse anything but a local database whose name ends in _test: the tests drop and recreate tables."""
    parsed = make_url(url)
    if parsed.host not in LOCAL_HOSTS:
        raise ValueError(
            f"TEST_DATABASE_URL must point to a local Postgres ({sorted(LOCAL_HOSTS)}), not {parsed.host!r}"
        )
    if not (parsed.database or "").endswith("_test"):
        raise ValueError(f"TEST_DATABASE_URL must name a database ending in _test, not {parsed.database!r}")
    return url


def database_url_or_skip() -> str:
    """The checked URL, or skip (locally) / fail (CI) when it is not set."""
    url = _TestDatabaseSettings().test_database_url
    if not url:
        if os.environ.get("CI") == "true":
            pytest.fail("TEST_DATABASE_URL is required in CI: the database tests must run there")
        pytest.skip("TEST_DATABASE_URL not set: database tests need the local Postgres (see .env.example)")
    return check_test_database_url(url)


def alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    # Passed as an attribute, not a main option, so a % in the password needs no escaping.
    config.attributes["sqlalchemy_url"] = url
    return config
