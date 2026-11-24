"""
Skill Lifecycle and Approval Manager.
Enforces strict human-in-the-loop governance for Skill promotions, rejections, and rollbacks.
"""

from __future__ import annotations

from typing import List, Optional
from libresprite_game_mcp.skills.models import (
    ApprovalAction,
    SkillApprovalRecord,
    SkillDefinition,
    SkillStatus,
)
from libresprite_game_mcp.skills.repository import SkillRepository


class AutonomousApprovalError(PermissionError):
    """Raised when an autonomous process attempts to approve a production Skill."""
    pass


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""
    pass


VALID_TRANSITIONS = {
    SkillStatus.DRAFT: {SkillStatus.SANDBOX, SkillStatus.DISABLED},
    SkillStatus.SANDBOX: {SkillStatus.APPROVED, SkillStatus.DRAFT, SkillStatus.DISABLED},
    SkillStatus.APPROVED: {SkillStatus.DEPRECATED, SkillStatus.DISABLED},
    SkillStatus.DEPRECATED: {SkillStatus.DISABLED, SkillStatus.APPROVED},
    SkillStatus.DISABLED: {SkillStatus.DRAFT, SkillStatus.APPROVED},
}

AUTONOMOUS_REVIEWERS = {
    "system",
    "agent",
    "autonomous",
    "llm",
    "skill_builder",
    "evaluator",
    "orchestrator",
    "bot",
    "ai",
}


class SkillLifecycleManager:
    """Governs Skill state transitions and human approval checks."""

    def __init__(self, repository: SkillRepository):
        self.repository = repository

    def submit_to_sandbox(self, skill_id: str, version: str) -> SkillDefinition:
        """Transitions a DRAFT skill to SANDBOX for evaluation."""
        return self._transition(
            skill_id=skill_id,
            version=version,
            target_status=SkillStatus.SANDBOX,
            reviewer="system",
            action=None,
            comments="Submitted to sandbox for automated benchmark and testing.",
        )

    def approve_skill(
        self,
        skill_id: str,
        version: str,
        reviewer: str,
        comments: str,
        human_confirmed: bool = True,
    ) -> SkillDefinition:
        """
        Approves a SANDBOX skill for production.
        STRICT REQUIREMENT: Explicit human confirmation and SANDBOX prerequisite state are mandatory.
        """
        if not human_confirmed:
            raise AutonomousApprovalError("Approval rejected: explicit human confirmation is required.")

        if not reviewer or not reviewer.strip():
            raise AutonomousApprovalError("Reviewer name is required for approval.")

        rev = reviewer.strip().lower()
        if any(bot in rev for bot in AUTONOMOUS_REVIEWERS):
            raise AutonomousApprovalError(
                f"Autonomous approval rejected for skill '{skill_id}' version '{version}'. "
                f"Reviewer '{reviewer}' matches automated agent or system pattern. "
                "Human Art Director or Technical Lead approval is strictly mandatory."
            )

        if not comments or len(comments.strip()) < 10:
            raise ValueError("Approval requires detailed justification comments (min 10 characters) from the human reviewer.")

        skill = self.repository.get_skill_version(skill_id, version)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' version '{version}' does not exist.")

        if skill.status != SkillStatus.SANDBOX:
            raise InvalidStateTransitionError(
                f"Cannot approve skill '{skill_id}' from state '{skill.status.value}'. "
                "Skill must be in SANDBOX state before human approval."
            )

        return self._transition(
            skill_id=skill_id,
            version=version,
            target_status=SkillStatus.APPROVED,
            reviewer=reviewer.strip(),
            action=ApprovalAction.APPROVED,
            comments=comments.strip(),
        )

    def reject_skill(
        self,
        skill_id: str,
        version: str,
        reviewer: str,
        comments: str,
    ) -> SkillDefinition:
        """Rejects a candidate skill from SANDBOX, moving it to DISABLED and logging REJECTED action."""
        return self._transition(
            skill_id=skill_id,
            version=version,
            target_status=SkillStatus.DISABLED,
            reviewer=reviewer.strip(),
            action=ApprovalAction.REJECTED,
            comments=comments.strip(),
        )

    def deprecate_skill(
        self,
        skill_id: str,
        version: str,
        reviewer: str,
        comments: str,
    ) -> SkillDefinition:
        """Marks an approved skill as DEPRECATED."""
        return self._transition(
            skill_id=skill_id,
            version=version,
            target_status=SkillStatus.DEPRECATED,
            reviewer=reviewer.strip(),
            action=ApprovalAction.DEPRECATED,
            comments=comments.strip(),
        )

    def rollback_skill(
        self,
        skill_id: str,
        from_version: str,
        to_version: str,
        reviewer: str,
        comments: str,
    ) -> SkillDefinition:
        """
        Rolls back production skill:
        Deprecates from_version and re-activates to_version as APPROVED.
        """
        # 1. Deprecate the faulty version
        self.deprecate_skill(
            skill_id=skill_id,
            version=from_version,
            reviewer=reviewer,
            comments=f"Rolled back to {to_version}. Reason: {comments}",
        )

        # 2. Re-approve the target rollback version
        return self._transition(
            skill_id=skill_id,
            version=to_version,
            target_status=SkillStatus.APPROVED,
            reviewer=reviewer,
            action=ApprovalAction.APPROVED,
            comments=f"Restored as active production version after rollback of {from_version}.",
        )

    def _transition(
        self,
        skill_id: str,
        version: str,
        target_status: SkillStatus,
        reviewer: str,
        action: Optional[ApprovalAction] = None,
        comments: Optional[str] = None,
    ) -> SkillDefinition:
        skill = self.repository.get_skill_version(skill_id, version)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' version '{version}' does not exist.")

        current_status = skill.status

        # If already at target status, log audit and return cleanly
        if current_status == target_status:
            return skill

        allowed_targets = VALID_TRANSITIONS.get(current_status, set())

        if target_status not in allowed_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition skill '{skill_id}' from {current_status.value} to {target_status.value}. "
                f"Allowed target states: {[s.value for s in allowed_targets]}"
            )

        return self.repository.update_skill_status(
            skill_id=skill_id,
            version=version,
            new_status=target_status,
            reviewer=reviewer,
            comments=comments,
            action=action,
        )
