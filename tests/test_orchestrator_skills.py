"""
Tests for Sprint 0.7: Orchestrator Integration & Reference Skill.
Verifies reference skill discovery, execution, telemetry recording,
feedback ingestion, knowledge guidance, and end-to-end integration.
"""

import pytest
from pathlib import Path
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.learning.models import KnowledgeCategory


@pytest.fixture
def orchestrator(tmp_path):
    orch = ProductionOrchestrator(
        db_path=":memory:",
        skills_dir=tmp_path / "skills",
    )
    yield orch
    orch.db.close()


def test_reference_skill_seeding_and_discovery(orchestrator):
    """Ensures reference skill 'pixel_character_consistency' is seeded and discoverable."""
    context = {"task_category": "character", "perspective": "top_down"}
    matching = orchestrator.find_applicable_skills(context, art_profile_name="DefaultGame")

    assert len(matching) >= 1
    ref_skill = matching[0]
    assert ref_skill.skill_id == "pixel_character_consistency"
    assert ref_skill.version == "1.0.0"
    assert ref_skill.status.value == "APPROVED"
    assert len(ref_skill.workflow) == 4


def test_reference_skill_execution_and_telemetry(orchestrator):
    """Executes 'pixel_character_consistency', verifies step outputs, and checks experience persistence."""
    result = orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={
            "character_id": "goblin_archer",
            "name": "Goblin Archer",
            "size": [16, 16],
            "proportion": "chibi_1_2",
            "outline_mode": "colored",
        },
        project_id="GameProject1",
    )

    assert result["status"] == "success"
    assert result["skill_id"] == "pixel_character_consistency"
    assert result["outcome"] == "success"
    assert "step_1_generate" in result["step_outputs"]
    assert "step_2_outline" in result["step_outputs"]
    assert "step_3_validate" in result["step_outputs"]
    assert "step_4_export" in result["step_outputs"]

    # Verify Experience record saved in database
    exp_id = result["experience_id"]
    exp = orchestrator.learning_repo.get_experience(exp_id)
    assert exp is not None
    assert exp.project_id == "GameProject1"
    assert exp.task_category == "character"
    assert "character" in exp.tags


def test_feedback_ingestion_and_confidence_propagation(orchestrator):
    """Records user feedback on a task execution and verifies knowledge confidence update."""
    # 1. Add knowledge rule
    rule = orchestrator.knowledge_manager.add_rule(
        rule_name="Top-Down Chibi Colored Outline Rule",
        category=KnowledgeCategory.OUTLINE,
        description="Ensure colored outlines are applied for contrast in top-down views",
        conditions={"task_category": "character"},
        recommendations={"outline_mode": "colored"},
        initial_confidence=0.7,
        project_id="ProjectZ",
    )

    # 2. Execute skill
    exec_result = orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "test_hero"},
        project_id="ProjectZ",
    )
    exp_id = exec_result["experience_id"]

    # 3. Submit positive feedback
    fb = orchestrator.record_feedback(
        experience_id=exp_id,
        feedback_type="approval",
        user_rating=5.0,
        notes="Flawless outline contrast!",
    )
    assert fb.id is not None
    assert fb.user_rating == 5.0

    # 4. Verify rule confidence increased
    updated_rule = orchestrator.learning_repo.get_knowledge(rule.id)
    assert updated_rule.confidence_score > 0.7


def test_learning_guidance_retrieval(orchestrator):
    """Retrieves formatted guidance incorporating Art Bible constraints."""
    orchestrator.knowledge_manager.add_rule(
        rule_name="Standard Retro Palette",
        category=KnowledgeCategory.PALETTE,
        description="DB16 for top-down retro games",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "db16", "outline_mode": "colored"},
        initial_confidence=0.85,
    )

    guidance = orchestrator.get_knowledge_guidance(
        task_category="character",
        resolution=(16, 16),
    )
    assert "db16" in guidance["palettes"]
    assert "colored" in guidance["outlines"]
    assert len(guidance["constraints"]) >= 1


def test_unapproved_skill_execution_rejected(orchestrator):
    """Confirms that attempting to execute an unapproved or draft skill in production fails."""
    with pytest.raises(ValueError) as exc_info:
        orchestrator.execute_skill(skill_id="unapproved_draft_skill")
    assert "is not available or not APPROVED" in str(exc_info.value)
