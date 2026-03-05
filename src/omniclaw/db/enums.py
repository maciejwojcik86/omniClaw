from enum import Enum


class NodeType(str, Enum):
    AGENT = "AGENT"
    HUMAN = "HUMAN"


class NodeStatus(str, Enum):
    DRAFT = "DRAFT"
    PROBATION = "PROBATION"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


class RelationshipType(str, Enum):
    MANAGES = "MANAGES"


class FormType(str, Enum):
    # Legacy constants kept for compatibility with earlier milestones.
    MESSAGE = "MESSAGE"
    BUDGET = "BUDGET"
    SPAWN_AGENT = "SPAWN_AGENT"
    SKILL_DEPLOY = "SKILL_DEPLOY"
    TASK_DELEGATION = "TASK_DELEGATION"


class FormStatus(str, Enum):
    DRAFT = "DRAFT"
    WAITING_TO_BE_READ = "WAITING_TO_BE_READ"
    SENT = "SENT"
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    ARCHIVED = "ARCHIVED"
    DEAD_LETTER = "DEAD_LETTER"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    RETURNED = "RETURNED"
    APPROVED = "APPROVED"


class SkillValidationStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_QA = "IN_QA"
    VALIDATED = "VALIDATED"
    DEPRECATED = "DEPRECATED"


class FormTypeLifecycle(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
