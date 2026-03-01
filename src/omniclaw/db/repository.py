from sqlalchemy.orm import Session, sessionmaker

from omniclaw.db.enums import NodeStatus, NodeType, RelationshipType
from omniclaw.db.models import Hierarchy, Node


class KernelRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def create_node(
        self,
        *,
        node_type: NodeType,
        name: str,
        status: NodeStatus,
        linux_uid: int | None = None,
        autonomy_level: int = 0,
    ) -> Node:
        with self._session_factory() as session:
            node = Node(
                type=node_type,
                name=name,
                status=status,
                linux_uid=linux_uid,
                autonomy_level=autonomy_level,
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            return node

    def upsert_node_by_name(
        self,
        *,
        node_type: NodeType,
        name: str,
        status: NodeStatus,
        linux_uid: int | None = None,
        autonomy_level: int = 0,
    ) -> tuple[Node, bool]:
        with self._session_factory() as session:
            existing = (
                session.query(Node)
                .filter(Node.type == node_type, Node.name == name)
                .order_by(Node.created_at.asc())
                .first()
            )
            if existing is not None:
                existing.status = status
                existing.linux_uid = linux_uid
                existing.autonomy_level = autonomy_level
                session.commit()
                session.refresh(existing)
                return existing, False

            created = Node(
                type=node_type,
                name=name,
                status=status,
                linux_uid=linux_uid,
                autonomy_level=autonomy_level,
            )
            session.add(created)
            session.commit()
            session.refresh(created)
            return created, True

    def link_manager(
        self,
        *,
        parent_node_id: str,
        child_node_id: str,
        relationship_type: RelationshipType = RelationshipType.MANAGES,
    ) -> Hierarchy:
        with self._session_factory() as session:
            link = Hierarchy(
                parent_node_id=parent_node_id,
                child_node_id=child_node_id,
                relationship_type=relationship_type,
            )
            session.add(link)
            session.commit()
            session.refresh(link)
            return link

    def link_manager_if_missing(
        self,
        *,
        parent_node_id: str,
        child_node_id: str,
        relationship_type: RelationshipType = RelationshipType.MANAGES,
    ) -> Hierarchy:
        with self._session_factory() as session:
            existing = (
                session.query(Hierarchy)
                .filter(
                    Hierarchy.parent_node_id == parent_node_id,
                    Hierarchy.child_node_id == child_node_id,
                )
                .order_by(Hierarchy.created_at.asc())
                .first()
            )
            if existing is not None:
                return existing

            link = Hierarchy(
                parent_node_id=parent_node_id,
                child_node_id=child_node_id,
                relationship_type=relationship_type,
            )
            session.add(link)
            session.commit()
            session.refresh(link)
            return link

    def list_children(self, *, parent_node_id: str) -> list[Hierarchy]:
        with self._session_factory() as session:
            return (
                session.query(Hierarchy)
                .filter(Hierarchy.parent_node_id == parent_node_id)
                .order_by(Hierarchy.created_at.asc())
                .all()
            )
