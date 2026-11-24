"""
Tests for Sprint 0.3: Architecture & Data Foundation.
Verifies Pydantic schemas, database migrations, foreign-key constraints,
transaction rollback, project isolation, semver validation, and skill immutability.
"""

import json
import sqlite3
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from libresprite_game_mcp.learning.models import (
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    OutcomeType,
)
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.skills.models import (
    ApprovalAction,
    SkillApprovalRecord,
    SkillDefinition,
    SkillEvaluationRecord,
    SkillExecutionResult,
    SkillStatus,
    WorkflowStep,
)
from libresprite_game_mcp.skills.repository import ImmutableSkillError, SkillRepository
from libresprite_game_mcp.skills.versioning import (
    bump_semver,
    compare_semver,
    is_valid_semver,
    parse_semver,
)
from libresprite_game_mcp.storage.database import DatabaseManager


# -----------------------------------------------------------------------------
# 1. Pydantic Schema Validation Tests
# -----------------------------------------------------------------------------
def test_experience_schema_validation():
    """Validates ExperienceRecord instantiation and field constraints."""
    exp = ExperienceRecord(
        task_id="task-001",
        task_category="character",
        asset_category="sprite",
        resolution=(32, 32),
        art_profile={"project_name": "TestGame", "palette": "db16"},
        tools_used=["generate_character"],
        input_context={"prompt": "warrior"},
        output_summary={"frame_count": 4},
        execution_time_ms=120.5,
        outcome=OutcomeType.SUCCESS,
        tags=["warrior", "chibi"],
    )
    assert exp.task_id == "task-001"
    assert exp.resolution == (32, 32)
    assert exp.outcome == OutcomeType.SUCCESS

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        ExperienceRecord(
            task_id="task-002",
            invalid_extra_field="malicious_payload",
        )


def test_feedback_schema_validation():
    """Validates FeedbackRecord rating bounds and forbidden extra fields."""
    fb = FeedbackRecord(
        experience_id="exp-123",
        feedback_type=FeedbackType.APPROVAL,
        user_rating=4.5,
        notes="Great silhouette",
    )
    assert fb.user_rating == 4.5

    # Out of range rating (< 1.0 or > 5.0) must fail
    with pytest.raises(ValidationError):
        FeedbackRecord(
            experience_id="exp-123",
            user_rating=6.0,
        )

    with pytest.raises(ValidationError):
        FeedbackRecord(
            experience_id="exp-123",
            user_rating=0.5,
        )


def test_knowledge_schema_validation():
    """Validates KnowledgeRecord confidence score range."""
    kr = KnowledgeRecord(
        category=KnowledgeCategory.OUTLINE,
        rule_name="No isolated stray pixels in 16x16",
        description="Clean orphan pixels on silhouettes",
        confidence_score=0.9,
    )
    assert kr.confidence_score == 0.9

    # Score > 1.0 or < 0.0 must fail
    with pytest.raises(ValidationError):
        KnowledgeRecord(
            category=KnowledgeCategory.OUTLINE,
            rule_name="Invalid",
            description="Score too high",
            confidence_score=1.5,
        )


def test_skill_definition_semver_validation():
    """Validates semver enforcement on SkillDefinition."""
    step = WorkflowStep(
        step_id="step_1",
        tool_name="generate_character",
        parameters={"size": (16, 16)},
    )
    skill = SkillDefinition(
        skill_id="chibi_generator",
        version="1.0.0",
        name="Chibi Character Generator",
        description="Generates 16x16 chibi characters",
        workflow=[step],
    )
    assert skill.version == "1.0.0"

    # Invalid SemVer must be rejected
    with pytest.raises(ValidationError):
        SkillDefinition(
            skill_id="chibi_generator",
            version="v1_invalid",
            name="Chibi Character Generator",
            description="Invalid version",
        )


def test_serialization_round_trip():
    """Ensures model_dump_json and model_validate_json preserve all types including datetimes."""
    exp = ExperienceRecord(
        task_id="task-003",
        task_category="animation",
        resolution=(16, 16),
        execution_time_ms=55.0,
    )
    json_data = exp.model_dump_json()
    assert isinstance(json_data, str)

    restored = ExperienceRecord.model_validate_json(json_data)
    assert restored.id == exp.id
    assert restored.task_id == exp.task_id
    assert restored.resolution == (16, 16)
    assert isinstance(restored.created_at, datetime)


# -----------------------------------------------------------------------------
# 2. Database & Repository Tests
# -----------------------------------------------------------------------------
@pytest.fixture
def test_db():
    """Provides a fresh in-memory database with migrations applied."""
    db = DatabaseManager(":memory:")
    yield db
    db.close()


def test_foreign_key_constraint(test_db):
    """Ensures foreign keys are strictly enforced on feedbacks table."""
    learning_repo = LearningRepository(test_db)
    orphan_fb = FeedbackRecord(
        experience_id="non-existent-exp-id",
        feedback_type=FeedbackType.APPROVAL,
    )

    with pytest.raises(sqlite3.IntegrityError):
        learning_repo.save_feedback(orphan_fb)


def test_cascade_delete(test_db):
    """Ensures deleting an experience automatically deletes associated feedbacks."""
    learning_repo = LearningRepository(test_db)
    exp = ExperienceRecord(
        task_id="task-del",
        task_category="tileset",
        resolution=(16, 16),
    )
    learning_repo.save_experience(exp)

    fb = FeedbackRecord(
        experience_id=exp.id,
        feedback_type=FeedbackType.CORRECTION,
        notes="Adjust contrast",
    )
    learning_repo.save_feedback(fb)

    # Verify feedback exists
    feedbacks = learning_repo.get_feedbacks_for_experience(exp.id)
    assert len(feedbacks) == 1

    # Delete experience
    deleted = learning_repo.delete_experience(exp.id)
    assert deleted is True

    # Associated feedback should be gone via ON DELETE CASCADE
    feedbacks_after = learning_repo.get_feedbacks_for_experience(exp.id)
    assert len(feedbacks_after) == 0


def test_transaction_rollback(test_db):
    """Ensures atomicity: failed operations roll back entire transaction."""
    learning_repo = LearningRepository(test_db)
    exp = ExperienceRecord(task_id="task-rollback", resolution=(16, 16))

    try:
        with test_db.transaction() as conn:
            # Step 1: Save valid experience
            learning_repo.save_experience(exp)
            # Step 2: Trigger intentional failure (e.g., duplicate primary key or bad SQL)
            conn.execute("INSERT INTO experiences (id, project_id) VALUES (NULL, NULL)")
    except Exception:
        pass  # Expected rollback

    # The experience should not exist because the transaction rolled back
    saved_exp = learning_repo.get_experience(exp.id)
    assert saved_exp is None


def test_project_isolation(test_db):
    """
    Ensures knowledge querying respects project boundaries:
    - Universal rules (project_id=None) are visible to all projects.
    - Project A cannot see Project B's rules.
    - An unauthenticated or universal query sees only universal rules.
    """
    learning_repo = LearningRepository(test_db)

    # 1. Universal Art Bible rule
    universal_rule = KnowledgeRecord(
        project_id=None,
        category=KnowledgeCategory.OUTLINE,
        rule_name="Universal Black Outline",
        description="Global rule for retro games",
        confidence_score=0.95,
    )
    learning_repo.save_knowledge(universal_rule)

    # 2. Project Alpha rule
    alpha_rule = KnowledgeRecord(
        project_id="ProjectAlpha",
        category=KnowledgeCategory.PALETTE,
        rule_name="Alpha Palette Restriction",
        description="Must use NES palette only",
        confidence_score=0.85,
    )
    learning_repo.save_knowledge(alpha_rule)

    # 3. Project Beta rule
    beta_rule = KnowledgeRecord(
        project_id="ProjectBeta",
        category=KnowledgeCategory.PALETTE,
        rule_name="Beta Palette Restriction",
        description="Must use GameBoy 4-color green",
        confidence_score=0.85,
    )
    learning_repo.save_knowledge(beta_rule)

    # Query for Project Alpha: must get alpha_rule + universal_rule, but NOT beta_rule
    alpha_results = learning_repo.query_knowledge(project_id="ProjectAlpha")
    alpha_ids = {r.id for r in alpha_results}
    assert universal_rule.id in alpha_ids
    assert alpha_rule.id in alpha_ids
    assert beta_rule.id not in alpha_ids

    # Query for Project Beta: must get beta_rule + universal_rule, but NOT alpha_rule
    beta_results = learning_repo.query_knowledge(project_id="ProjectBeta")
    beta_ids = {r.id for r in beta_results}
    assert universal_rule.id in beta_ids
    assert beta_rule.id in beta_ids
    assert alpha_rule.id not in beta_ids

    # Query with no project_id (universal only)
    universal_results = learning_repo.query_knowledge(project_id=None)
    universal_ids = {r.id for r in universal_results}
    assert universal_rule.id in universal_ids
    assert alpha_rule.id not in universal_ids
    assert beta_rule.id not in universal_ids


def test_skill_immutability(test_db):
    """
    Verifies that APPROVED skill versions cannot be mutated.
    Updates require creating a new semver version.
    """
    skill_repo = SkillRepository(test_db)

    skill_v1 = SkillDefinition(
        skill_id="sword_generator",
        version="1.0.0",
        name="Sword Generator",
        description="Generates standard 16x16 swords",
        status=SkillStatus.DRAFT,
    )
    skill_repo.save_skill_definition(skill_v1)

    # While in DRAFT, it can be updated
    skill_v1.description = "Updated description in draft"
    skill_repo.save_skill_definition(skill_v1)
    retrieved = skill_repo.get_skill_version("sword_generator", "1.0.0")
    assert retrieved.description == "Updated description in draft"

    # Promote to APPROVED
    approved_skill = skill_repo.update_skill_status(
        skill_id="sword_generator",
        version="1.0.0",
        new_status=SkillStatus.APPROVED,
        reviewer="ArtDirector",
        comments="Approved for production",
    )
    assert approved_skill.status == SkillStatus.APPROVED

    # Now attempt to modify the APPROVED 1.0.0 version -> must raise ImmutableSkillError
    approved_skill.description = "Malicious or unauthorized alteration"
    with pytest.raises(ImmutableSkillError):
        skill_repo.save_skill_definition(approved_skill)

    # To introduce changes, a new semver version must be used (e.g. 1.1.0)
    skill_v2 = SkillDefinition(
        skill_id="sword_generator",
        version=bump_semver("1.0.0", "minor"),
        name="Sword Generator",
        description="Enhanced sword generator with elemental glow",
        status=SkillStatus.DRAFT,
    )
    skill_repo.save_skill_definition(skill_v2)

    v1_check = skill_repo.get_skill_version("sword_generator", "1.0.0")
    v2_check = skill_repo.get_skill_version("sword_generator", "1.1.0")
    assert v1_check.status == SkillStatus.APPROVED
    assert v2_check.status == SkillStatus.DRAFT
    assert v2_check.description == "Enhanced sword generator with elemental glow"


def test_semver_utilities():
    """Verifies semver parsing, comparison, and bumping."""
    assert is_valid_semver("1.0.0") is True
    assert is_valid_semver("0.1.0-alpha") is True
    assert is_valid_semver("invalid.ver") is False

    assert parse_semver("2.4.11") == (2, 4, 11)

    assert compare_semver("1.0.0", "1.0.1") == -1
    assert compare_semver("1.2.0", "1.1.9") == 1
    assert compare_semver("2.0.0", "2.0.0") == 0

    assert bump_semver("1.2.3", "patch") == "1.2.4"
    assert bump_semver("1.2.3", "minor") == "1.3.0"
    assert bump_semver("1.2.3", "major") == "2.0.0"
