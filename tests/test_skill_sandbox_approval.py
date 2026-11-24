"""
Tests for Sprint 0.6: Sandbox Evaluation & Human Approval.
Verifies sandbox test execution, scoring, strict human approval gates,
invalid state transition protection, and version rollback.
"""

import pytest
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
from libresprite_game_mcp.skills.repository import SkillRepository
from libresprite_game_mcp.skills.sandbox import SandboxEvaluator, SkillTestCase
from libresprite_game_mcp.storage.database import DatabaseManager


@pytest.fixture
def lifecycle_env():
    db = DatabaseManager(":memory:")
    repo = SkillRepository(db)
    lifecycle = SkillLifecycleManager(repo)
    evaluator = SandboxEvaluator(repo)
    yield repo, lifecycle, evaluator
    db.close()


def _create_sample_skill(repo: SkillRepository, skill_id="chibi_walk", version="1.0.0", status=SkillStatus.DRAFT):
    skill = SkillDefinition(
        skill_id=skill_id,
        version=version,
        name="Chibi Walk Cycle",
        description="Generates 4-frame walk cycle",
        status=status,
        workflow=[
            WorkflowStep(step_id="step_1", tool_name="generate_character", parameters={"proportion": "chibi_1_2"}),
            WorkflowStep(step_id="step_2", tool_name="apply_outline", parameters={"mode": "colored"}),
        ],
    )
    return repo.save_skill_definition(skill)


# -----------------------------------------------------------------------------
# 1. Sandbox Evaluation Tests
# -----------------------------------------------------------------------------
def test_sandbox_evaluation_passing(lifecycle_env):
    repo, _lifecycle, evaluator = lifecycle_env
    skill = _create_sample_skill(repo)

    test_cases = [
        SkillTestCase(
            name="Chibi Warrior Test",
            input_parameters={"character_id": "warrior_01", "size": (16, 16)},
            expected_outputs={"outline_applied": True},
        ),
        SkillTestCase(
            name="Chibi Mage Test",
            input_parameters={"character_id": "mage_01", "size": (16, 16)},
            expected_outputs={"outline_applied": True},
        ),
    ]

    eval_record = evaluator.evaluate_skill(skill, test_cases)
    assert eval_record.score == 1.0
    assert eval_record.test_cases_run == 2
    assert eval_record.test_cases_passed == 2
    assert "2/2 test cases passed" in eval_record.evaluation_summary

    # Telemetry records must have been recorded
    executions = repo.get_execution_results(skill.skill_id, skill.version)
    assert len(executions) == 2


def test_sandbox_evaluation_partial_failure(lifecycle_env):
    repo, _lifecycle, evaluator = lifecycle_env
    skill = _create_sample_skill(repo)

    test_cases = [
        SkillTestCase(
            name="Passing Test",
            input_parameters={"character_id": "pass"},
            expected_outputs={"outline_applied": True},
        ),
        SkillTestCase(
            name="Failing Test",
            input_parameters={"character_id": "fail"},
            expected_outputs={"non_existent_key": 999},  # Will fail expected check
        ),
    ]

    eval_record = evaluator.evaluate_skill(skill, test_cases)
    assert eval_record.score == 0.5
    assert eval_record.test_cases_run == 2
    assert eval_record.test_cases_passed == 1


# -----------------------------------------------------------------------------
# 2. Strict Human Approval & State Machine Tests
# -----------------------------------------------------------------------------
def test_strict_human_approval_enforcement(lifecycle_env):
    repo, lifecycle, _evaluator = lifecycle_env
    skill = _create_sample_skill(repo)

    # 1. DRAFT -> SANDBOX
    sandbox_skill = lifecycle.submit_to_sandbox(skill.skill_id, skill.version)
    assert sandbox_skill.status == SkillStatus.SANDBOX

    # 2. Autonomous agent attempts to approve -> REJECTED with AutonomousApprovalError!
    with pytest.raises(AutonomousApprovalError) as exc_info:
        lifecycle.approve_skill(
            skill_id=skill.skill_id,
            version=skill.version,
            reviewer="autonomous_agent",
            comments="Looks good to LLM agent",
        )
    assert "Human Art Director or Technical Lead approval is strictly mandatory" in str(exc_info.value)

    # 3. System attempts to approve -> REJECTED
    with pytest.raises(AutonomousApprovalError):
        lifecycle.approve_skill(
            skill_id=skill.skill_id,
            version=skill.version,
            reviewer="system",
            comments="Automated system approval",
        )

    # 4. Human reviewer approves -> SUCCEEDS
    approved_skill = lifecycle.approve_skill(
        skill_id=skill.skill_id,
        version=skill.version,
        reviewer="ArtDirector_Sarah",
        comments="Approved after reviewing visual consistency in sandbox test cases.",
    )
    assert approved_skill.status == SkillStatus.APPROVED

    # Audit records check
    approvals = repo.get_approvals(skill.skill_id, skill.version)
    assert len(approvals) >= 1
    assert approvals[0].action == ApprovalAction.APPROVED
    assert approvals[0].reviewer == "ArtDirector_Sarah"


def test_invalid_state_transitions(lifecycle_env):
    repo, lifecycle, _evaluator = lifecycle_env
    skill = _create_sample_skill(repo)  # DRAFT

    # DRAFT directly to APPROVED is illegal (must pass through SANDBOX)
    with pytest.raises(InvalidStateTransitionError):
        lifecycle.approve_skill(
            skill_id=skill.skill_id,
            version=skill.version,
            reviewer="ArtDirector_Sarah",
            comments="Trying to skip sandbox",
        )


def test_skill_rollback(lifecycle_env):
    repo, lifecycle, _evaluator = lifecycle_env

    # 1. Setup v1.0.0 (APPROVED)
    skill_v1 = _create_sample_skill(repo, version="1.0.0", status=SkillStatus.APPROVED)

    # 2. Setup v1.1.0 (APPROVED)
    skill_v2 = _create_sample_skill(repo, version="1.1.0", status=SkillStatus.APPROVED)

    # v1.1.0 is latest approved
    latest = repo.get_latest_approved_skill(skill_v1.skill_id)
    assert latest.version == "1.1.0"

    # 3. Perform Rollback: roll back from 1.1.0 to 1.0.0
    restored = lifecycle.rollback_skill(
        skill_id=skill_v1.skill_id,
        from_version="1.1.0",
        to_version="1.0.0",
        reviewer="TechnicalLead_Alex",
        comments="v1.1.0 caused regression in frame alignment; restoring stable 1.0.0.",
    )

    assert restored.version == "1.0.0"
    assert restored.status == SkillStatus.APPROVED

    # Check that v1.1.0 is now DEPRECATED
    v1_1_check = repo.get_skill_version(skill_v1.skill_id, "1.1.0")
    assert v1_1_check.status == SkillStatus.DEPRECATED

    # Latest approved is now 1.0.0
    latest_after = repo.get_latest_approved_skill(skill_v1.skill_id)
    assert latest_after.version == "1.0.0"
