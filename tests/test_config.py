from sqlalchemy.engine import make_url

from core.config import Settings


def settings(**values) -> Settings:
    # _env_file=None keeps a developer's real .env out of the test.
    return Settings(_env_file=None, **values)


def test_password_with_url_characters_survives():
    password = "p@ss:w/rd#?"
    url = settings(postgres_password=password).sqlalchemy_url()
    assert make_url(url).password == password


def test_url_built_from_parts():
    url = make_url(settings(postgres_host="postgres", postgres_port=5432).sqlalchemy_url())
    assert (url.drivername, url.host, url.port, url.database) == ("postgresql+asyncpg", "postgres", 5432, "wi")


def test_explicit_database_url_wins():
    assert settings(database_url="postgresql+asyncpg://u:p@h:1/d").sqlalchemy_url() == "postgresql+asyncpg://u:p@h:1/d"


def test_empty_database_url_falls_back_to_parts():
    assert make_url(settings(database_url="").sqlalchemy_url()).host == "localhost"
