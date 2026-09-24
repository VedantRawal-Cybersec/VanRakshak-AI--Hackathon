from app.db import sqlalchemy_database_url


def test_postgres_url_uses_psycopg_v3_driver():
    assert sqlalchemy_database_url("postgresql://u:p@db:5432/app")=="postgresql+psycopg://u:p@db:5432/app"
    assert sqlalchemy_database_url("postgres://u:p@db:5432/app")=="postgresql+psycopg://u:p@db:5432/app"


def test_sqlite_url_is_unchanged():
    assert sqlalchemy_database_url("sqlite:///./test.db")=="sqlite:///./test.db"
