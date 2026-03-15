from pathlib import Path
from urllib.parse import unquote, urlparse

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from omniclaw.db.base import Base
from omniclaw.db import models as _models  # noqa: F401


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    if database_url.endswith(":memory:"):
        return

    parsed = urlparse(database_url)
    raw_path = unquote(parsed.path or "")
    if not raw_path:
        return

    if database_url.startswith("sqlite:////"):
        sqlite_path = Path(raw_path)
    else:
        sqlite_path = Path(raw_path.lstrip("/"))
    if sqlite_path.name == "":
        return

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_url(database_url: str) -> Engine:
    _ensure_sqlite_parent_dir(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def create_session_factory(database_url: str, engine: Engine | None = None) -> sessionmaker[Session]:
    resolved_engine = engine or create_engine_from_url(database_url)
    return sessionmaker(bind=resolved_engine, autocommit=False, autoflush=False, future=True)


def get_session_factory(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine_from_url(database_url)
    return engine, create_session_factory(database_url, engine=engine)


def require_database_at_head(database_url: str, engine: Engine | None = None) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    alembic_ini = repo_root / "alembic.ini"
    script_location = repo_root / "alembic"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", database_url)
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    expected_heads = set(heads)

    resolved_engine = engine or create_engine_from_url(database_url)
    with resolved_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    if current_revision not in expected_heads:
        expected = ", ".join(heads) if heads else "none"
        current = current_revision or "none"
        raise RuntimeError(
            "Database revision is not at Alembic head "
            f"(current={current}, expected={expected}). "
            "Run `uv run alembic upgrade head` before starting the kernel."
        )


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
