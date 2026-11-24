"""
Repository for Skill definitions, versioning, execution telemetry, evaluations, and approvals.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from libresprite_game_mcp.skills.models import (
    ApprovalAction,
    SkillApprovalRecord,
    SkillDefinition,
    SkillEvaluationRecord,
    SkillExecutionResult,
    SkillStatus,
    WorkflowStep,
)
from libresprite_game_mcp.skills.versioning import compare_semver
from libresprite_game_mcp.storage.database import DatabaseManager


class ImmutableSkillError(Exception):
    """Raised when an attempt is made to modify an already APPROVED Skill version."""
    pass


class SkillRepository:
    """Manages persistence and versioning constraints for Skills."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_skill_definition(self, skill: SkillDefinition, force: bool = False) -> SkillDefinition:
        """
        Saves a SkillDefinition.
        Enforces immutability: If this version already exists with status APPROVED,
        it cannot be overwritten. Any update requires bumping the semver version.
        """
        conn = self.db.get_connection()
        existing = conn.execute(
            "SELECT status FROM skill_versions WHERE skill_id = ? AND version = ?",
            (skill.skill_id, skill.version),
        ).fetchone()

        if existing and existing["status"] == SkillStatus.APPROVED.value:
            raise ImmutableSkillError(
                f"Skill '{skill.skill_id}' version '{skill.version}' is APPROVED and immutable. "
                "Bump the semver version to introduce changes."
            )

        with self.db.transaction() as t_conn:
            # 1. Upsert skill master
            t_conn.execute(
                """
                INSERT INTO skills (skill_id, name, description, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description
                """,
                (skill.skill_id, skill.name, skill.description, skill.created_at.isoformat()),
            )

            # 2. Upsert skill version
            workflow_json = json.dumps([step.model_dump() for step in skill.workflow])
            t_conn.execute(
                """
                INSERT INTO skill_versions (
                    skill_id, version, name, description, status,
                    trigger_conditions, required_tools, parameters_schema,
                    workflow, validation_rules, art_profile_compatibility,
                    author, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(skill_id, version) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    status=excluded.status,
                    trigger_conditions=excluded.trigger_conditions,
                    required_tools=excluded.required_tools,
                    parameters_schema=excluded.parameters_schema,
                    workflow=excluded.workflow,
                    validation_rules=excluded.validation_rules,
                    art_profile_compatibility=excluded.art_profile_compatibility,
                    author=excluded.author,
                    updated_at=excluded.updated_at
                """,
                (
                    skill.skill_id,
                    skill.version,
                    skill.name,
                    skill.description,
                    skill.status.value,
                    json.dumps(skill.trigger_conditions),
                    json.dumps(skill.required_tools),
                    json.dumps(skill.parameters_schema),
                    workflow_json,
                    json.dumps(skill.validation_rules),
                    json.dumps(skill.art_profile_compatibility),
                    skill.author,
                    skill.created_at.isoformat(),
                    skill.updated_at.isoformat(),
                ),
            )
        return skill

    def get_skill_version(self, skill_id: str, version: str) -> Optional[SkillDefinition]:
        """Retrieves a specific version of a Skill."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT * FROM skill_versions WHERE skill_id = ? AND version = ?",
            (skill_id, version),
        ).fetchone()
        if not row:
            return None
        return self._row_to_skill(row)

    def get_latest_approved_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Returns the highest semver APPROVED version for a skill, or None."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM skill_versions WHERE skill_id = ? AND status = ?",
            (skill_id, SkillStatus.APPROVED.value),
        ).fetchall()
        if not rows:
            return None
        skills = [self._row_to_skill(r) for r in rows]
        skills.sort(key=lambda s: s.version, reverse=True)
        # Sort using compare_semver properly
        from functools import cmp_to_key
        skills.sort(key=cmp_to_key(lambda a, b: compare_semver(a.version, b.version)), reverse=True)
        return skills[0]

    def list_skills(self, status: Optional[SkillStatus] = None) -> List[SkillDefinition]:
        """Lists skills optionally filtered by status."""
        conn = self.db.get_connection()
        if status:
            rows = conn.execute(
                "SELECT * FROM skill_versions WHERE status = ? ORDER BY skill_id, created_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM skill_versions ORDER BY skill_id, created_at DESC"
            ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def list_versions_for_skill(self, skill_id: str) -> List[SkillDefinition]:
        """Lists all versions of a given skill."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM skill_versions WHERE skill_id = ?",
            (skill_id,),
        ).fetchall()
        from functools import cmp_to_key
        skills = [self._row_to_skill(r) for r in rows]
        skills.sort(key=cmp_to_key(lambda a, b: compare_semver(a.version, b.version)), reverse=True)
        return skills

    def update_skill_status(
        self,
        skill_id: str,
        version: str,
        new_status: SkillStatus,
        reviewer: str = "human",
        comments: Optional[str] = None,
        action: Optional[ApprovalAction] = None,
    ) -> SkillDefinition:
        """Transitions skill version status and records an audit approval log when applicable."""
        skill = self.get_skill_version(skill_id, version)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' version '{version}' not found.")

        now = datetime.now(timezone.utc)
        skill.status = new_status
        skill.updated_at = now

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE skill_versions
                SET status = ?, updated_at = ?
                WHERE skill_id = ? AND version = ?
                """,
                (new_status.value, now.isoformat(), skill_id, version),
            )

            # Record approval/transition audit only for approval, rejection, or deprecation actions
            record_action = action
            if record_action is None:
                if new_status == SkillStatus.APPROVED:
                    record_action = ApprovalAction.APPROVED
                elif new_status in (SkillStatus.DISABLED, SkillStatus.DEPRECATED):
                    record_action = ApprovalAction.REJECTED

            if record_action is not None:
                approval = SkillApprovalRecord(
                    skill_id=skill_id,
                    skill_version=version,
                    action=record_action,
                    reviewer=reviewer,
                    comments=comments,
                    timestamp=now,
                )
                conn.execute(
                    """
                    INSERT INTO skill_approvals (id, skill_id, skill_version, action, reviewer, comments, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval.id,
                        approval.skill_id,
                        approval.skill_version,
                        approval.action.value,
                        approval.reviewer,
                        approval.comments,
                        approval.timestamp.isoformat(),
                    ),
                )

        return skill

    # -------------------------------------------------------------------------
    # Execution Telemetry
    # -------------------------------------------------------------------------
    def save_execution_result(self, result: SkillExecutionResult) -> SkillExecutionResult:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_executions (
                    id, skill_id, skill_version, project_id, execution_context,
                    status, outputs, qa_passed, execution_duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.skill_id,
                    result.skill_version,
                    result.project_id,
                    json.dumps(result.execution_context),
                    result.status,
                    json.dumps(result.outputs),
                    1 if result.qa_passed else 0,
                    result.execution_duration_ms,
                    result.created_at.isoformat(),
                ),
            )
        return result

    def get_execution_results(
        self,
        skill_id: str,
        version: Optional[str] = None,
        limit: int = 50,
    ) -> List[SkillExecutionResult]:
        clauses = ["skill_id = ?"]
        params: List[Any] = [skill_id]
        if version:
            clauses.append("skill_version = ?")
            params.append(version)
        sql = f"SELECT * FROM skill_executions WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self.db.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [
            SkillExecutionResult(
                id=r["id"],
                skill_id=r["skill_id"],
                skill_version=r["skill_version"],
                project_id=r["project_id"],
                execution_context=json.loads(r["execution_context"]),
                status=r["status"],
                outputs=json.loads(r["outputs"]),
                qa_passed=bool(r["qa_passed"]),
                execution_duration_ms=float(r["execution_duration_ms"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    # -------------------------------------------------------------------------
    # Sandbox Evaluation Records
    # -------------------------------------------------------------------------
    def save_evaluation(self, eval_rec: SkillEvaluationRecord) -> SkillEvaluationRecord:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_evaluations (
                    id, skill_id, skill_version, test_cases_run,
                    test_cases_passed, score, evaluation_summary, details, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_rec.id,
                    eval_rec.skill_id,
                    eval_rec.skill_version,
                    eval_rec.test_cases_run,
                    eval_rec.test_cases_passed,
                    eval_rec.score,
                    eval_rec.evaluation_summary,
                    json.dumps(eval_rec.details),
                    eval_rec.created_at.isoformat(),
                ),
            )
        return eval_rec

    def get_evaluations(self, skill_id: str, version: Optional[str] = None) -> List[SkillEvaluationRecord]:
        clauses = ["skill_id = ?"]
        params: List[Any] = [skill_id]
        if version:
            clauses.append("skill_version = ?")
            params.append(version)
        sql = f"SELECT * FROM skill_evaluations WHERE {' AND '.join(clauses)} ORDER BY created_at DESC"

        conn = self.db.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [
            SkillEvaluationRecord(
                id=r["id"],
                skill_id=r["skill_id"],
                skill_version=r["skill_version"],
                test_cases_run=int(r["test_cases_run"]),
                test_cases_passed=int(r["test_cases_passed"]),
                score=float(r["score"]),
                evaluation_summary=r["evaluation_summary"],
                details=json.loads(r["details"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    # -------------------------------------------------------------------------
    # Approvals Audit
    # -------------------------------------------------------------------------
    def get_approvals(self, skill_id: str, version: Optional[str] = None) -> List[SkillApprovalRecord]:
        clauses = ["skill_id = ?"]
        params: List[Any] = [skill_id]
        if version:
            clauses.append("skill_version = ?")
            params.append(version)
        sql = f"SELECT * FROM skill_approvals WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC, rowid DESC"

        conn = self.db.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [
            SkillApprovalRecord(
                id=r["id"],
                skill_id=r["skill_id"],
                skill_version=r["skill_version"],
                action=ApprovalAction(r["action"]),
                reviewer=r["reviewer"],
                comments=r["comments"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]

    def _row_to_skill(self, row: Any) -> SkillDefinition:
        workflow_data = json.loads(row["workflow"])
        workflow_steps = [WorkflowStep.model_validate(step) for step in workflow_data]
        return SkillDefinition(
            skill_id=row["skill_id"],
            version=row["version"],
            name=row["name"],
            description=row["description"],
            status=SkillStatus(row["status"]),
            trigger_conditions=json.loads(row["trigger_conditions"]),
            required_tools=json.loads(row["required_tools"]),
            parameters_schema=json.loads(row["parameters_schema"]),
            workflow=workflow_steps,
            validation_rules=json.loads(row["validation_rules"]),
            art_profile_compatibility=json.loads(row["art_profile_compatibility"]),
            author=row["author"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
