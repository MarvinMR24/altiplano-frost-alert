"""SQLite engine and sessions. Tables are created with create_all (no Alembic)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        path = database_url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record) -> None:
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def init_db(engine: Engine) -> sessionmaker[Session]:
    from . import models  # noqa: F401  (registers the tables)

    Base.metadata.create_all(engine)
    _migrate_users(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _migrate_users(engine: Engine) -> None:
    """Idempotent startup migration for the password auth columns.

    `create_all` never adds columns to an existing SQLite file, so add the missing ones
    with ALTER TABLE. Every row that predates the migration logged in with an email code,
    which proves ownership of the address, so existing rows are marked verified. No data
    is dropped.
    """
    from sqlalchemy import inspect, text

    with engine.begin() as conn:
        if "users" not in inspect(conn).get_table_names():
            return
        columns = {c["name"] for c in inspect(conn).get_columns("users")}
        missing = {"password_hash", "phone", "email_verified"} - columns
        if "password_hash" in missing:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(200)"))
        if "phone" in missing:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
        if "email_verified" in missing:
            conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0 NOT NULL"))
            conn.execute(text("UPDATE users SET email_verified = 1"))


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    db = factory()
    try:
        yield db
    finally:
        db.close()
