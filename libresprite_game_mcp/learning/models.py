"""
Learning Layer Data Models.
Structured schemas for Experiences, Feedback, and Knowledge Records.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class OutcomeType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class FeedbackType(str, Enum):
    APPROVAL = "approval"
    REJECTION = "rejection"
    CORRECTION = "correction"
    PREFERENCE = "preference"


class KnowledgeCategory(str, Enum):
    PALETTE = "palette"
    LIGHTING = "lighting"
    SILHOUETTE = "silhouette"
    OUTLINE = "outline"
    DITHERING = "dithering"
    ANIMATION_TIMING = "animation_timing"
    COMPOSITION = "composition"
    GENERAL = "general"


class ExperienceRecord(BaseModel):
    """Execution experience captured from agent or tool runs."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    project_id: str = "default"
    task_id: str
    task_category: str = Field(
        default="general",
        description="character, tileset, item, animation, ui, general"
    )
    asset_category: str = "sprite"
    resolution: Tuple[int, int] = (16, 16)
    art_profile: Dict[str, Any] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    input_context: Dict[str, Any] = Field(default_factory=dict)
    output_summary: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    execution_outcome: str = "SUCCESS"  # "SUCCESS", "FAILED"
    validation_outcome: str = "SKIPPED"  # "PASSED", "FAILED", "SKIPPED"
    qa_outcome: str = "SKIPPED"  # "PASSED", "CRITICAL_FAIL", "WARNINGS", "SKIPPED"
    human_acceptance: Optional[str] = None  # "APPROVED", "REJECTED", "CORRECTED", "PENDING"
    outcome: OutcomeType = OutcomeType.SUCCESS
    qa_report: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=_utc_now)
    tags: List[str] = Field(default_factory=list)


class FeedbackRecord(BaseModel):
    """User feedback, approval/rejection, or manual correction."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    experience_id: str
    project_id: str = "default"
    feedback_type: FeedbackType = FeedbackType.APPROVAL
    user_rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    notes: Optional[str] = None
    suggested_changes: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


class KnowledgeRecord(BaseModel):
    """Consolidated rule, heuristic, or learned constraint."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_new_id)
    project_id: Optional[str] = Field(
        default=None,
        description="None indicates universal Art Bible knowledge; string indicates project-specific rule."
    )
    category: KnowledgeCategory = KnowledgeCategory.GENERAL
    rule_name: str
    description: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    recommendations: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_experience_ids: List[str] = Field(default_factory=list)
    applied_feedback_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
