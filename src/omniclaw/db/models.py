from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from omniclaw.db.base import Base
from omniclaw.db.enums import (
    FormStatus,
    FormType,
    NodeStatus,
    NodeType,
    RelationshipType,
    SkillValidationStatus,
)


def _uuid_str() -> str:
    return str(uuid4())


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    type: Mapped[NodeType] = mapped_column(
        Enum(NodeType, name="node_type", native_enum=False, validate_strings=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    linux_uid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    autonomy_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[NodeStatus] = mapped_column(
        Enum(NodeStatus, name="node_status", native_enum=False, validate_strings=True),
        nullable=False,
        default=NodeStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Hierarchy(Base):
    __tablename__ = "hierarchy"
    __table_args__ = (UniqueConstraint("parent_node_id", "child_node_id", name="uq_hierarchy_parent_child"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    parent_node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    child_node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType, name="relationship_type", native_enum=False, validate_strings=True),
        nullable=False,
        default=RelationshipType.MANAGES,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, unique=True)
    daily_limit_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    per_task_cap_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    virtual_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_node_id: Mapped[str | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)
    allocated_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    current_daily_allowance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    current_spend: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FormLedger(Base):
    __tablename__ = "forms_ledger"

    form_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[FormType] = mapped_column(
        Enum(FormType, name="form_type", native_enum=False, validate_strings=True), nullable=False
    )
    current_status: Mapped[FormStatus] = mapped_column(
        Enum(FormStatus, name="form_status", native_enum=False, validate_strings=True),
        nullable=False,
        default=FormStatus.DRAFT,
    )
    current_holder_node: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    history_log: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MasterSkill(Base):
    __tablename__ = "master_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    execution_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_status: Mapped[SkillValidationStatus] = mapped_column(
        Enum(
            SkillValidationStatus,
            name="skill_validation_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        default=SkillValidationStatus.DRAFT,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1.0")
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

