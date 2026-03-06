from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from omniclaw.db.base import Base
from omniclaw.db.enums import (
    FormTypeLifecycle,
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
    linux_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linux_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_root: Mapped[str | None] = mapped_column(String(512), nullable=True)
    runtime_config_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    primary_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway_running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gateway_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gateway_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gateway_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gateway_stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    __table_args__ = (
        UniqueConstraint("parent_node_id", "child_node_id", name="uq_hierarchy_parent_child"),
        UniqueConstraint("child_node_id", name="uq_hierarchy_child_manager"),
    )

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
    type: Mapped[str] = mapped_column(String(128), nullable=False, default="message")
    form_type_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    form_type_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_status: Mapped[str] = mapped_column(String(64), nullable=False, default=FormStatus.DRAFT.value)
    current_holder_node: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    message_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    target_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    delivery_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    archive_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dead_letter_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    routed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": version}
    history_log: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FormTypeDefinition(Base):
    __tablename__ = "form_types"
    __table_args__ = (UniqueConstraint("type_key", "version", name="uq_form_types_type_key_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    type_key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_state: Mapped[FormTypeLifecycle] = mapped_column(
        Enum(FormTypeLifecycle, name="form_type_lifecycle", native_enum=False, validate_strings=True),
        nullable=False,
        default=FormTypeLifecycle.DRAFT,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_graph: Mapped[str] = mapped_column(Text, nullable=False)
    stage_metadata: Mapped[str] = mapped_column(Text, nullable=False)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FormTransitionEvent(Base):
    __tablename__ = "form_transition_events"
    __table_args__ = (UniqueConstraint("form_id", "sequence", name="uq_form_transition_events_form_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    form_id: Mapped[str] = mapped_column(ForeignKey("forms_ledger.form_id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_node_id: Mapped[str | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)
    previous_holder_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    new_holder_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MasterSkill(Base):
    __tablename__ = "master_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    form_type_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    master_path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="1.0.0")
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
