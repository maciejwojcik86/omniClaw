from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_engine_from_url, create_session_factory, init_db


def test_repository_creates_nodes_and_hierarchy(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'repo.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)

    repository = KernelRepository(create_session_factory(database_url))
    parent = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Human_01",
        status=NodeStatus.ACTIVE,
    )
    child = repository.create_node(
        node_type=NodeType.AGENT,
        name="Agent_01",
        status=NodeStatus.PROBATION,
        linux_uid=12001,
        autonomy_level=1,
    )

    link = repository.link_manager(parent_node_id=parent.id, child_node_id=child.id)
    children = repository.list_children(parent_node_id=parent.id)

    assert link.parent_node_id == parent.id
    assert link.child_node_id == child.id
    assert len(children) == 1
    assert children[0].child_node_id == child.id


def test_alembic_upgrade_creates_canonical_tables(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine_from_url(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {
        "nodes",
        "hierarchy",
        "budgets",
        "forms_ledger",
        "master_skills",
    }.issubset(tables)

