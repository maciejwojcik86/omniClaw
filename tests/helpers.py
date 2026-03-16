import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from omniclaw.global_config import default_company_entry


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


def write_global_company_config(
    *,
    path: Path,
    workspace_root: Path,
    slug: str = "test-company",
    display_name: str = "Test Company",
    instructions: dict[str, Any] | None = None,
    budgeting: dict[str, Any] | None = None,
    hierarchy: dict[str, Any] | None = None,
    skills: dict[str, Any] | None = None,
    models: list[dict[str, Any]] | None = None,
    runtime: dict[str, Any] | None = None,
) -> Path:
    entry_payload = default_company_entry(
        slug=slug,
        display_name=display_name,
        workspace_root=workspace_root,
    ).to_payload()
    if instructions is not None:
        entry_payload["instructions"] = instructions
    if budgeting is not None:
        entry_payload["budgeting"] = budgeting
    if hierarchy is not None:
        entry_payload["hierarchy"] = hierarchy
    if skills is not None:
        entry_payload["skills"] = skills
    if models is not None:
        entry_payload["models"] = models
    if runtime is not None:
        entry_payload["runtime"] = runtime

    payload = {
        "schema_version": 1,
        "companies": {
            slug: entry_payload,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
