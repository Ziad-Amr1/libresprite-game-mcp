"""
Sprint 0.8 Corrective Integration & Production Readiness Regression Test Suite.

Verifies all seven core corrective objectives:
- Objective A: Real MCP tool binding & fail-closed contracts
- Objective B: Deterministic workflow execution engine & DAG validation
- Objective C: Real asset QA enforcement on disk
- Objective D: Sandbox separation & isolated evaluation modes
- Objective E: Human approval enforcement & Skill immutability
- Objective F: Learning Layer reliability, failure capture, & feedback idempotency
- Objective G: Evidence-based multi-experience skill synthesis & provenance
"""

import json
import os
import tempfile
from pathlib import Path
import pytest
from PIL import Image

from libresprite_game_mcp.core.dispatcher import (
    ExecutionMode,
    MockToolDispatcher,
    ProductionToolDispatcher,
    ToolExecutionError,
)
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.core.workflow_engine import (
    StepResult,
    WorkflowEngine,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from libresprite_game_mcp.learning.models import (
    FeedbackType,
    KnowledgeCategory,
    OutcomeType,
)
from libresprite_game_mcp.skills.builder import APPROVED_MCP_TOOLS, SkillBuilder
from libresprite_game_mcp.skills.lifecycle import (
    AutonomousApprovalError,
    InvalidStateTransitionError,
    SkillLifecycleManager,
)
from libresprite_game_mcp.skills.models import (
    ApprovalAction,
    SkillDefinition,
    SkillStatus,
    WorkflowStep,
)
from libresprite_game_mcp.skills.repository import (
    ImmutableSkillError,
    SkillRepository,
)
from libresprite_game_mcp.skills.sandbox import SandboxEvaluator, SkillTestCase
from libresprite_game_mcp.storage.database import DatabaseManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "test_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_learning.db"
    db = DatabaseManager(db_file)
    yield db
    db.close()


@pytest.fixture
def orchestrator(isolated_db, temp_workspace):
    orch = ProductionOrchestrator(
        db_path=isolated_db.db_path,
        assets_dir=temp_workspace,
        mode=ExecutionMode.PRODUCTION,
    )
    return orch


# =============================================================================
# Objective A: Real MCP Tool Binding & Contracts
# =============================================================================

def test_objective_a_real_tool_execution(temp_workspace):
    """Verifies real production tools execute and generate valid filesystem artifacts."""
    dispatcher = ProductionToolDispatcher()
    
    # 1. generate_character creates actual .aseprite file and preview PNG
    out = dispatcher.dispatch(
        "generate_character",
        {
            "character_id": "knight_hero",
            "name": "Knight Hero",
            "size": [16, 16],
            "proportion": "chibi_1_2",
            "palette_name": "db16",
        },
        temp_workspace,
    )
    
    project_file = Path(out["project_path"])
    preview_file = Path(out["preview_path"])
    assert project_file.exists()
    assert preview_file.exists()
    assert project_file.stat().st_size > 0
    assert preview_file.stat().st_size > 0
    
    # Verify preview image format
    with Image.open(preview_file) as img:
        assert img.size == (16, 16)
        assert img.mode == "RGBA"


def test_objective_a_dispatcher_fails_closed_on_unknown_tool(temp_workspace):
    """Verifies dispatcher strictly rejects un-allowlisted tools."""
    dispatcher = ProductionToolDispatcher()
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch("arbitrary_system_command", {"cmd": "rm -rf /"}, temp_workspace)
    assert "arbitrary_system_command' is not registered" in str(exc_info.value)


def test_objective_a_dispatcher_fails_closed_missing_params(temp_workspace):
    """Verifies dispatcher fails closed if mandatory tool parameters are missing."""
    dispatcher = ProductionToolDispatcher()
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch("apply_outline", {}, temp_workspace)
    assert "requires 'project_path' or 'input_file'" in str(exc_info.value)


# =============================================================================
# Objective B: Workflow Execution Engine & DAG Validation
# =============================================================================

def test_objective_b_dag_validation_cycles_and_duplicates():
    """Verifies workflow engine detects duplicate step IDs and illegal dependencies."""
    engine = WorkflowEngine(mode=ExecutionMode.MOCK)
    
    # Duplicate step_id
    dup_steps = [
        WorkflowStep(step_id="step_1", tool_name="generate_character", parameters={}),
        WorkflowStep(step_id="step_1", tool_name="apply_outline", parameters={}),
    ]
    valid, errors = engine.validate_dag(dup_steps)
    assert not valid
    assert any("Duplicate step_id 'step_1'" in e for e in errors)
    
    # Invalid dependency referencing a future/non-preceding step
    forward_ref = [
        WorkflowStep(step_id="step_1", tool_name="generate_character", parameters={"source_step": "step_2"}),
        WorkflowStep(step_id="step_2", tool_name="apply_outline", parameters={}),
    ]
    valid, errors = engine.validate_dag(forward_ref)
    assert not valid
    assert any("references 'source_step': 'step_2' which is not a preceding step" in e for e in errors)


def test_objective_b_workflow_halts_on_step_failure(temp_workspace):
    """Verifies that when a step fails, subsequent steps are marked skipped and not executed."""
    engine = WorkflowEngine(dispatcher=ProductionToolDispatcher(), mode=ExecutionMode.PRODUCTION)
    
    skill = SkillDefinition(
        skill_id="failing_workflow_test",
        version="1.0.0",
        name="Failing Workflow Test",
        description="Tests failure halt semantics",
        status=SkillStatus.APPROVED,
        workflow=[
            WorkflowStep(
                step_id="step_1_ok",
                tool_name="generate_character",
                parameters={"character_id": "test_ch"},
            ),
            WorkflowStep(
                step_id="step_2_fail",
                tool_name="apply_outline",
                parameters={"project_path": str(temp_workspace / "non_existent_file.aseprite")},
            ),
            WorkflowStep(
                step_id="step_3_skipped",
                tool_name="export_godot_spritesheet",
                parameters={"source_step": "step_1_ok"},
            ),
        ],
    )
    
    res = engine.execute(skill=skill, workspace=temp_workspace)
    assert res.status == WorkflowStatus.FAILED
    assert res.step_results["step_1_ok"].status == "success"
    assert res.step_results["step_2_fail"].status == "failed"
    assert res.step_results["step_3_skipped"].status == "skipped"


# =============================================================================
# Objective C: Real Asset QA Enforcement on Disk
# =============================================================================

def test_objective_c_qa_failure_halts_downstream_export(temp_workspace):
    """Verifies that QA critical failures halt execution before export when require_qa_pass=True."""
    engine = WorkflowEngine(dispatcher=ProductionToolDispatcher(), mode=ExecutionMode.PRODUCTION)
    
    # Generate a character
    dispatcher = ProductionToolDispatcher()
    char_out = dispatcher.dispatch(
        "generate_character",
        {"character_id": "hero_qa", "size": [16, 16]},
        temp_workspace,
    )
    
    # Create workflow where expected_size is 32x32, which will fail dimension QA
    skill = SkillDefinition(
        skill_id="qa_enforcement_test",
        version="1.0.0",
        name="QA Enforcement Test",
        description="Tests QA failure halt",
        status=SkillStatus.APPROVED,
        workflow=[
            WorkflowStep(
                step_id="step_1_qa",
                tool_name="validate_asset",
                parameters={
                    "project_path": char_out["project_path"],
                    "expected_size": [32, 32],  # Actual is 16x16, will FAIL
                },
            ),
            WorkflowStep(
                step_id="step_2_export",
                tool_name="export_godot_spritesheet",
                parameters={"source_step": "step_1_qa"},
            ),
        ],
        validation_rules={"require_qa_pass": True},
    )
    
    res = engine.execute(skill=skill, workspace=temp_workspace)
    assert res.status == WorkflowStatus.FAILED
    assert res.step_results["step_1_qa"].status == "failed"
    assert "critical_errors" in res.step_results["step_1_qa"].outputs
    assert res.step_results["step_2_export"].status == "skipped"
    # Ensure godot export was not generated
    assert not (temp_workspace / "hero_qa_sheet.png").exists()


# =============================================================================
# Objective D: Sandbox Separation & Isolated Modes
# =============================================================================

def test_objective_d_sandbox_evaluation_isolation_and_step_outputs(temp_workspace, isolated_db):
    """Verifies sandbox evaluator operates in an isolated directory and validates expected step outputs."""
    repo = SkillRepository(isolated_db)
    evaluator = SandboxEvaluator(
        repository=repo,
        mode=ExecutionMode.SANDBOX,
        sandbox_base_dir=temp_workspace / "sandbox_runs",
    )
    
    skill = SkillDefinition(
        skill_id="sandbox_isolation_skill",
        version="1.0.0",
        name="Sandbox Isolation Skill",
        description="Sandbox evaluation testing",
        status=SkillStatus.DRAFT,
        workflow=[
            WorkflowStep(
                step_id="step_generate",
                tool_name="generate_character",
                parameters={"character_id": "sandbox_hero", "size": [16, 16]},
            ),
            WorkflowStep(
                step_id="step_outline",
                tool_name="apply_outline",
                parameters={"mode": "colored", "source_step": "step_generate"},
            ),
        ],
    )
    repo.save_skill_definition(skill)
    
    test_case = SkillTestCase(
        name="Step Output Verification Test",
        input_parameters={"size": [16, 16]},
        expected_step_outputs={
            "step_outline": {"outline_applied": True, "mode": "colored"}
        },
        qa_must_pass=False,
    )
    
    eval_rec = evaluator.evaluate_skill(skill, [test_case])
    assert eval_rec.score == 1.0
    assert eval_rec.test_cases_passed == 1
    assert eval_rec.details["execution_mode"] == "SANDBOX"


# =============================================================================
# Objective E: Skill Governance & Immutability
# =============================================================================

def test_objective_e_reference_skills_seeded_as_draft(orchestrator):
    """Verifies reference skills are seeded as DRAFT and cannot be executed in production until approved."""
    skill = orchestrator.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
    assert skill is not None
    assert skill.status == SkillStatus.DRAFT
    
    # Attempting to execute unapproved skill in PRODUCTION mode must fail
    with pytest.raises(ValueError) as exc_info:
        orchestrator.execute_skill("pixel_character_consistency", parameters={})
    assert "is not available or not APPROVED for execution in [PRODUCTION] mode" in str(exc_info.value)


def test_objective_e_strict_human_approval_gates(isolated_db):
    """Verifies autonomous approval is rejected and human confirmation is required."""
    repo = SkillRepository(isolated_db)
    lifecycle = SkillLifecycleManager(repo)
    
    skill = SkillDefinition(
        skill_id="gov_test_skill",
        version="1.0.0",
        name="Gov Test",
        description="Testing governance gates",
        status=SkillStatus.DRAFT,
        required_tools=["generate_character"],
    )
    repo.save_skill_definition(skill)
    
    # 1. Direct approval from DRAFT fails (must be SANDBOX)
    with pytest.raises(InvalidStateTransitionError):
        lifecycle.approve_skill(
            skill_id="gov_test_skill",
            version="1.0.0",
            reviewer="ArtDirector_Alex",
            comments="Skipping sandbox",
        )
    
    # Move to SANDBOX
    lifecycle.submit_to_sandbox("gov_test_skill", "1.0.0")
    
    # 2. Autonomous reviewer rejected
    with pytest.raises(AutonomousApprovalError):
        lifecycle.approve_skill(
            skill_id="gov_test_skill",
            version="1.0.0",
            reviewer="autonomous_llm_agent",
            comments="Looks great to an LLM",
        )
    
    # 3. Missing human confirmation flag rejected
    with pytest.raises(AutonomousApprovalError):
        lifecycle.approve_skill(
            skill_id="gov_test_skill",
            version="1.0.0",
            reviewer="ArtDirector_Alex",
            comments="Approving without confirmation token",
            human_confirmed=False,
        )
    
    # 4. Valid human approval succeeds
    approved = lifecycle.approve_skill(
        skill_id="gov_test_skill",
        version="1.0.0",
        reviewer="ArtDirector_Alex",
        comments="Approved following thorough visual inspection in sandbox.",
        human_confirmed=True,
    )
    assert approved.status == SkillStatus.APPROVED


def test_objective_e_approved_skill_immutability(isolated_db):
    """Verifies that an APPROVED skill cannot be modified or overwritten."""
    repo = SkillRepository(isolated_db)
    lifecycle = SkillLifecycleManager(repo)
    
    skill = SkillDefinition(
        skill_id="immutable_skill",
        version="1.0.0",
        name="Immutable Skill",
        description="Testing immutability",
        status=SkillStatus.DRAFT,
        required_tools=["generate_character"],
    )
    repo.save_skill_definition(skill)
    lifecycle.submit_to_sandbox("immutable_skill", "1.0.0")
    lifecycle.approve_skill(
        skill_id="immutable_skill",
        version="1.0.0",
        reviewer="Lead_Tech_Artist",
        comments="Approved for production immutability test.",
        human_confirmed=True,
    )
    
    # Attempting to save modification on APPROVED version must raise ImmutableSkillError
    mutated_skill = skill.model_copy()
    mutated_skill.description = "Tampered description after approval"
    with pytest.raises(ImmutableSkillError):
        repo.save_skill_definition(mutated_skill)


# =============================================================================
# Objective F: Learning Layer Reliability & Feedback Idempotency
# =============================================================================

def test_objective_f_experience_recorded_on_unhandled_failure(orchestrator, temp_workspace):
    """Verifies experience capture is guaranteed via try/finally even if execution crashes."""
    orchestrator.approve_reference_skill("pixel_character_consistency")
    
    # Trigger execution with invalid palette that causes tool failure
    res = orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"palette_name": "NON_EXISTENT_INVALID_PALETTE_9999"},
        project_id="CrashTestProject",
        workspace=temp_workspace,
    )
    
    assert res["status"] == "failed"
    exp_id = res["experience_id"]
    exp = orchestrator.learning_repo.get_experience(exp_id)
    assert exp is not None
    assert exp.outcome == OutcomeType.FAILURE
    assert exp.execution_outcome == "FAILED"


def test_objective_f_feedback_idempotency_and_category_relevance(orchestrator, temp_workspace):
    """Verifies duplicate feedback does not inflate confidence, and feedback updates relevant rules only."""
    orchestrator.approve_reference_skill("pixel_character_consistency")
    
    # 1. Add outline rule
    outline_rule = orchestrator.knowledge_manager.add_rule(
        rule_name="Top-Down Outline Rule",
        category=KnowledgeCategory.OUTLINE,
        description="Outlines enhance visibility in top down view",
        conditions={"task_category": "character"},
        initial_confidence=0.5,
        project_id="ProjectF",
    )
    
    # 2. Add irrelevant palette rule
    palette_rule = orchestrator.knowledge_manager.add_rule(
        rule_name="Dungeon Dark Palette Rule",
        category=KnowledgeCategory.PALETTE,
        description="Dark tones for dungeons",
        conditions={"task_category": "environment"},
        initial_confidence=0.5,
        project_id="ProjectF",
    )
    
    # 3. Execute skill
    res = orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "hero_f"},
        project_id="ProjectF",
        workspace=temp_workspace,
    )
    assert res["status"] == "success"
    
    # 4. Ingest outline-specific feedback
    fb1 = orchestrator.record_feedback(
        experience_id=res["experience_id"],
        feedback_type="approval",
        user_rating=5.0,
        notes="High quality outline work",
        idempotency_key="unique_key_12345",
    )
    
    upd_outline = orchestrator.learning_repo.get_knowledge(outline_rule.id)
    upd_palette = orchestrator.learning_repo.get_knowledge(palette_rule.id)
    
    # Outline confidence increased
    assert upd_outline.confidence_score > 0.5
    # Irrelevant palette confidence unchanged
    assert upd_palette.confidence_score == 0.5
    
    # 5. Ingest duplicate feedback with same idempotency key -> MUST NOT CHANGE SCORE
    score_after_fb1 = upd_outline.confidence_score
    fb2 = orchestrator.record_feedback(
        experience_id=res["experience_id"],
        feedback_type="approval",
        user_rating=5.0,
        notes="High quality outline work",
        idempotency_key="unique_key_12345",
    )
    
    upd_outline_again = orchestrator.learning_repo.get_knowledge(outline_rule.id)
    assert upd_outline_again.confidence_score == score_after_fb1


# =============================================================================
# Objective G: Evidence-Based Multi-Experience Skill Synthesis
# =============================================================================

def test_objective_g_skill_synthesis_multi_experience_consensus(isolated_db):
    """Verifies skill synthesis requires min_experiences >= 3, detects conflicts, and outputs DRAFT."""
    from libresprite_game_mcp.learning.collector import ExperienceCollector
    from libresprite_game_mcp.learning.repository import LearningRepository
    
    learn_repo = LearningRepository(isolated_db)
    collector = ExperienceCollector(learn_repo)
    builder = SkillBuilder()
    
    # 1. Attempting synthesis with only 2 experiences must fail consensus check
    for i in range(2):
        collector.record_task_run(
            task_id=f"synth_task_{i}",
            task_category="character",
            asset_category="sprite",
            resolution=(16, 16),
            input_context={"character_id": f"char_{i}"},
            output_summary={},
            tools_used=["generate_character", "apply_outline", "validate_asset"],
            execution_time_ms=100.0,
            execution_outcome="SUCCESS",
            art_profile={"name": "RetroFantasy"},
            project_id="ConsensusProject",
        )
    
    exps_2 = learn_repo.query_experiences(project_id="ConsensusProject")
    with pytest.raises(ValueError) as exc_info:
        builder.synthesize_draft_from_experiences(
            experiences=exps_2,
            skill_id="synth_skill",
            name="Synthesized Skill",
            description="Generated from consensus",
            min_experiences=3,
        )
    assert "Insufficient evidence: found 2 experiences, minimum required is 3" in str(exc_info.value)
    
    # 2. Add 3rd matching experience -> synthesis succeeds
    collector.record_task_run(
        task_id="synth_task_2",
        task_category="character",
        asset_category="sprite",
        resolution=(16, 16),
        input_context={"character_id": "char_2"},
        output_summary={},
        tools_used=["generate_character", "apply_outline", "validate_asset"],
        execution_time_ms=105.0,
        execution_outcome="SUCCESS",
        art_profile={"name": "RetroFantasy"},
        project_id="ConsensusProject",
    )
    
    exps_3 = learn_repo.query_experiences(project_id="ConsensusProject")
    draft_skill = builder.synthesize_draft_from_experiences(
        experiences=exps_3,
        skill_id="synth_skill",
        name="Synthesized Skill",
        description="Generated from consensus",
        min_experiences=3,
    )
    
    assert draft_skill is not None
    assert draft_skill.status == SkillStatus.DRAFT  # Never auto-approved
    assert len(draft_skill.validation_rules["synthesized_from_experiences"]) == 3
    assert [s.tool_name for s in draft_skill.workflow] == [
        "generate_character",
        "apply_outline",
        "validate_asset",
    ]
