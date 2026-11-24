"""
Learning Layer Data Models.
Structured schemas for Experiences, Feedback, and Knowledge Records.
Separates External Reference, Empirical Knowledge, Human Feedback, and Validated Skills.
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


class KnowledgeType(str, Enum):
    """Explicitly separates the four tiers of learned and reference knowledge."""
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"      # Techniques from articles, tutorials, master artists
    EMPIRICAL_KNOWLEDGE = "EMPIRICAL_KNOWLEDGE"    # Patterns supported by repeated generation runs & QA
    HUMAN_FEEDBACK = "HUMAN_FEEDBACK"              # User corrections, ratings, preferences, approvals
    VALIDATED_SKILL = "VALIDATED_SKILL"            # Reusable workflows passing sandbox & human approval


class EvidenceStatus(str, Enum):
    """Tracks validation status of reference knowledge without pseudo-probabilities."""
    REFERENCE_GUIDANCE = "REFERENCE_GUIDANCE"      # From tutorials/literature, unverified in production
    COMMUNITY_CONSENSUS = "COMMUNITY_CONSENSUS"    # Widely accepted industry standard principle
    EMPIRICAL_OBSERVATION = "EMPIRICAL_OBSERVATION"# Derived from engine execution telemetry
    HUMAN_DIRECTIVE = "HUMAN_DIRECTIVE"            # Explicit user preference or art director mandate


class KnowledgeCategory(str, Enum):
    PALETTE = "palette"
    LIGHTING = "lighting"
    SILHOUETTE = "silhouette"
    OUTLINE = "outline"
    DITHERING = "dithering"
    ANIMATION_TIMING = "animation_timing"
    COMPOSITION = "composition"
    GENERAL = "general"


class ReferenceProvenance(BaseModel):
    """Retains origin, author, citation, and applicability boundaries for external references."""
    model_config = ConfigDict(extra="forbid")

    source_title: str
    author: str
    source_url: str
    access_date: str  # YYYY-MM-DD
    extracted_principle: str
    interpretation: str
    applicable_asset_categories: List[str] = Field(default_factory=lambda: ["character"])
    applicable_resolutions: List[str] = Field(default_factory=list)
    applicable_styles: List[str] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)
    validation_status: str = "TUTORIAL_REFERENCE"  # "TUTORIAL_REFERENCE", "COMMUNITY_CONSENSUS", "SUPERSEDED"


class CharacterGenerationGuidance(BaseModel):
    """Explicit, typed guidance package delivered from Learning Layer to Character Generator."""
    model_config = ConfigDict(extra="forbid")

    target_resolution: Tuple[int, int] = (16, 16)
    selected_art_profile: str = "DefaultGame"
    character_archetype: Optional[str] = None
    palette_constraints: List[str] = Field(default_factory=list)
    silhouette_recommendations: Dict[str, Any] = Field(default_factory=dict)
    shading_recommendations: Dict[str, Any] = Field(default_factory=dict)
    outline_recommendations: Dict[str, Any] = Field(default_factory=dict)
    animation_requirements: Dict[str, Any] = Field(default_factory=dict)
    applicable_rules: List[str] = Field(default_factory=list)


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
    knowledge_type: KnowledgeType = KnowledgeType.EMPIRICAL_KNOWLEDGE
    evidence_status: EvidenceStatus = EvidenceStatus.EMPIRICAL_OBSERVATION
    category: KnowledgeCategory = KnowledgeCategory.GENERAL
    rule_name: str
    description: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    recommendations: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Empirical confidence score (0.0-1.0). None for External References."
    )
    provenance: Optional[ReferenceProvenance] = None
    source_experience_ids: List[str] = Field(default_factory=list)
    applied_feedback_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
