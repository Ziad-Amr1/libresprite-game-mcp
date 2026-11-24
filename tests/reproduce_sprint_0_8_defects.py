"""
Reproduction script demonstrating defects identified in Sprint 0.8:
1. Tool Binding: ProductionOrchestrator uses mock dispatcher by default (no real files created).
2. Workflow: source_step dependencies are ignored and not resolved.
3. QA: Mock QA passes without checking real files.
4. Governance: Reference skill is seeded as APPROVED with force=True, bypassing approval workflow.
5. Learning: Exceptions during execution escape without recording an ExperienceRecord; feedback blindly updates unrelated rules.
6. Skill Synthesis: Only considers the first experience and ignores contradictory evidence.
"""

import pytest
from pathlib import Path

from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.learning.models import KnowledgeCategory
from libresprite_game_mcp.skills.builder import SkillBuilder
from libresprite_game_mcp.skills.models import SkillStatus, WorkflowStep
from libresprite_game_mcp.storage.database import DatabaseManager


def test_defect_1_production_orchestrator_uses_mock_dispatcher_by_default(tmp_path):
    """Defect 1: execute_skill returns success but creates NO real files on disk because it uses mock dispatcher."""
    orch = ProductionOrchestrator(db_path=":memory:", skills_dir=tmp_path / "skills")
    
    # Execute the default seeded skill
    result = orch.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "real_knight", "size": [16, 16]},
        project_id="test_proj"
    )
    
    # The dispatcher returned fake success
    assert result["status"] == "success"
    # But notice: step_1_generate returned a fake dict and didn't create any file on disk!
    gen_output = result["step_outputs"]["step_1_generate"]
    assert "character_id" in gen_output
    # No file path was produced, no real file exists
    assert "file_path" not in gen_output
    orch.db.close()


def test_defect_2_dependency_resolution_unresolved(tmp_path):
    """Defect 2: step_2 has 'source_step': 'step_1_generate', but receives none of step 1's outputs."""
    orch = ProductionOrchestrator(db_path=":memory:", skills_dir=tmp_path / "skills")
    
    skill = orch.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
    step_2 = skill.workflow[1]
    assert step_2.parameters.get("source_step") == "step_1_generate"
    
    result = orch.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "hero"},
    )
    
    # Step 2 output did not consume or reference anything from step 1
    step_2_out = result["step_outputs"]["step_2_outline"]
    assert step_2_out.get("outline_applied") is True  # Fake mock response
    orch.db.close()


def test_defect_3_reference_skill_seeded_approved(tmp_path):
    """Defect 3: Reference skills are seeded directly as APPROVED, bypassing human approval."""
    orch = ProductionOrchestrator(db_path=":memory:", skills_dir=tmp_path / "skills")
    
    skill = orch.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
    # Defect: It is already APPROVED without any human review audit trail
    assert skill.status == SkillStatus.APPROVED
    
    approvals = orch.skill_repo.get_approvals("pixel_character_consistency", "1.0.0")
    # No human approval record exists!
    assert len(approvals) == 0
    orch.db.close()


def test_defect_4_unhandled_failure_escapes_without_experience_record(tmp_path):
    """Defect 4: When a tool throws an exception, execute_skill fails without creating an ExperienceRecord."""
    def failing_dispatcher(tool_name, params):
        raise RuntimeError("Simulated crash in generator")
        
    orch = ProductionOrchestrator(
        db_path=":memory:",
        skills_dir=tmp_path / "skills",
        tool_dispatcher=failing_dispatcher
    )
    
    with pytest.raises(RuntimeError):
        orch.execute_skill("pixel_character_consistency")
        
    # Check experiences: it should be 0 because the exception escaped before record_task_run
    experiences = orch.learning_repo.query_experiences(limit=10)
    assert len(experiences) == 0, "Defect confirmed: failed run left no trace in Learning Layer!"
    orch.db.close()


def test_defect_5_feedback_updates_unrelated_rules_and_lacks_idempotency(tmp_path):
    """Defect 5: Feedback updates all rules in task_category, even if completely unrelated, and lacks idempotency."""
    orch = ProductionOrchestrator(db_path=":memory:", skills_dir=tmp_path / "skills")
    
    # Rule 1: Outline
    rule_outline = orch.knowledge_manager.add_rule(
        rule_name="Outline Rule",
        category=KnowledgeCategory.OUTLINE,
        description="Outline rule",
        conditions={"task_category": "character"},
        initial_confidence=0.5,
    )
    # Rule 2: Palette (Unrelated to outline!)
    rule_palette = orch.knowledge_manager.add_rule(
        rule_name="Palette Rule",
        category=KnowledgeCategory.PALETTE,
        description="Palette rule",
        conditions={"task_category": "character"},
        initial_confidence=0.5,
    )
    
    # Run a skill
    res = orch.execute_skill("pixel_character_consistency")
    exp_id = res["experience_id"]
    
    # User provides feedback specifically saying: "Outline contrast was great"
    orch.record_feedback(experience_id=exp_id, feedback_type="approval", user_rating=5.0, notes="Outline contrast was great")
    
    # Defect: Palette rule confidence was also increased even though feedback was about outline!
    up_palette = orch.learning_repo.get_knowledge(rule_palette.id)
    assert up_palette.confidence_score > 0.5, "Defect confirmed: unrelated rule updated!"
    
    # Defect: Submitting the exact same feedback again increases confidence AGAIN (no idempotency)
    orch.record_feedback(experience_id=exp_id, feedback_type="approval", user_rating=5.0, notes="Outline contrast was great")
    up_palette_2 = orch.learning_repo.get_knowledge(rule_palette.id)
    assert up_palette_2.confidence_score > up_palette.confidence_score, "Defect confirmed: no idempotency protection!"
    orch.db.close()
