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
    BUDGET = "BUDGET"
    SPAWN_AGENT = "SPAWN_AGENT"
    SKILL_DEPLOY = "SKILL_DEPLOY"
    TASK_DELEGATION = "TASK_DELEGATION"


class FormStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    RETURNED = "RETURNED"
    APPROVED = "APPROVED"


class SkillValidationStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_QA = "IN_QA"
    VALIDATED = "VALIDATED"
    DEPRECATED = "DEPRECATED"

