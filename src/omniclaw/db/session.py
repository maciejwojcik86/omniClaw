from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from omniclaw.db.base import Base
from omniclaw.db import models as _models  # noqa: F401


def create_engine_from_url(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def create_session_factory(database_url: str, engine: Engine | None = None) -> sessionmaker[Session]:
    resolved_engine = engine or create_engine_from_url(database_url)
    return sessionmaker(bind=resolved_engine, autocommit=False, autoflush=False, future=True)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
