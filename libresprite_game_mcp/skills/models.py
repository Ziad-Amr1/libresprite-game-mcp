"""
Skill Builder Data Models.
Structured definitions for Skills, Workflows, Execution Results, Sandbox Evaluations, and Approvals.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from libresprite_game_mcp.skills.versioning import is_valid_semver


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class SkillStatus(str, Enum):
    DRAFT = "DRAFT"
    SANDBOX = "SANDBOX"
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


class ApprovalAction(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


class WorkflowStep(BaseModel):
    """A single deterministic execution step in a Skill workflow."""
    model_config = ConfigDict(extra="forbid")

    step_id: str
    tool_name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_output_type: str = "dict"


class SkillDefinition(BaseModel):
    """Declarative specification of a reusable production Skill."""
    model_config = ConfigDict(extra="forbid")

    skill_id: str
    version: str = "1.0.0"
    name: str
    description: str
    status: SkillStatus = SkillStatus.DRAFT
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)
    required_tools: List[str] = Field(default_factory=list)
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    workflow: List[WorkflowStep] = Field(default_factory=list)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    art_profile_compatibility: List[str] = Field(default_factory=list)
    author: str = "system"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("version")
    @classmethod
    def validate_version_semver(cls, v: str) -> str:
        if not is_valid_semver(v):
            raise ValueError(f"Version '{v}' is not a valid Semantic Version (expected X.Y.Z)")
        return v


class SkillExecutionResult(BaseModel):
    """Outcome and telemetry from running a Skill."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    skill_id: str
    skill_version: str
    project_id: str = "default"
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="success", description="success, failed, error")
    outputs: Dict[str, Any] = Field(default_factory=dict)
    qa_passed: bool = True
    execution_duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=_utc_now)


class SkillEvaluationRecord(BaseModel):
    """Sandbox benchmark and automated evaluation report for a Skill version."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    skill_id: str
    skill_version: str
    test_cases_run: int = Field(default=0, ge=0)
    test_cases_passed: int = Field(default=0, ge=0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    evaluation_summary: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)


class SkillApprovalRecord(BaseModel):
    """Audit record for human review and state transition of a Skill version."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    skill_id: str
    skill_version: str
    action: ApprovalAction = ApprovalAction.APPROVED
    reviewer: str
    comments: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utc_now)
