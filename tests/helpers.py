from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]


def migrate_database_to_head(database_url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    # Tests rely on workspace-seeded stage-graph message workflow via ensure_builtin_message_form_type.
    # Migration history may leave a legacy active message workflow graph, so clear it after upgrade.
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM form_types WHERE type_key = 'message'"))
