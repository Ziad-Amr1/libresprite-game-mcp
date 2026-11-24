"""
Repository pattern for Learning Layer data access (Experiences, Feedback, Knowledge).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from libresprite_game_mcp.learning.models import (
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
    OutcomeType,
)
from libresprite_game_mcp.storage.database import DatabaseManager


class LearningRepository:
    """Manages persistence and queries for Experiences, Feedback, and Knowledge."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # -------------------------------------------------------------------------
    # Experience Operations
    # -------------------------------------------------------------------------
    def save_experience(self, record: ExperienceRecord) -> ExperienceRecord:
        """Saves or updates an ExperienceRecord."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO experiences (
                    id, project_id, task_id, task_category, asset_category,
                    resolution, art_profile, tools_used, input_context,
                    output_summary, execution_time_ms, execution_outcome,
                    validation_outcome, qa_outcome, human_acceptance,
                    outcome, qa_report, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id=excluded.project_id,
                    task_id=excluded.task_id,
                    task_category=excluded.task_category,
                    asset_category=excluded.asset_category,
                    resolution=excluded.resolution,
                    art_profile=excluded.art_profile,
                    tools_used=excluded.tools_used,
                    input_context=excluded.input_context,
                    output_summary=excluded.output_summary,
                    execution_time_ms=excluded.execution_time_ms,
                    execution_outcome=excluded.execution_outcome,
                    validation_outcome=excluded.validation_outcome,
                    qa_outcome=excluded.qa_outcome,
                    human_acceptance=excluded.human_acceptance,
                    outcome=excluded.outcome,
                    qa_report=excluded.qa_report,
                    tags=excluded.tags,
                    created_at=excluded.created_at
                """,
                (
                    record.id,
                    record.project_id,
                    record.task_id,
                    record.task_category,
                    record.asset_category,
                    f"{record.resolution[0]}x{record.resolution[1]}",
                    json.dumps(record.art_profile),
                    json.dumps(record.tools_used),
                    json.dumps(record.input_context),
                    json.dumps(record.output_summary),
                    record.execution_time_ms,
                    record.execution_outcome,
                    record.validation_outcome,
                    record.qa_outcome,
                    record.human_acceptance,
                    record.outcome.value if isinstance(record.outcome, OutcomeType) else str(record.outcome),
                    json.dumps(record.qa_report) if record.qa_report else None,
                    json.dumps(record.tags),
                    record.created_at.isoformat(),
                ),
            )
        return record

    def get_experience(self, exp_id: str) -> Optional[ExperienceRecord]:
        """Retrieves an ExperienceRecord by ID."""
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM experiences WHERE id = ?", (exp_id,)).fetchone()
        if not row:
            return None
        return self._row_to_experience(row)

    def query_experiences(
        self,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExperienceRecord]:
        """Queries experiences matching filter criteria."""
        clauses = []
        params = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if task_category is not None:
            clauses.append("task_category = ?")
            params.append(task_category)
        if outcome is not None:
            clauses.append("outcome = ?")
            params.append(outcome)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM experiences {where_sql} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self.db.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_experience(r) for r in rows]

    def delete_experience(self, exp_id: str) -> bool:
        """Deletes an experience (cascades to feedbacks)."""
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM experiences WHERE id = ?", (exp_id,))
            return cur.rowcount > 0

    def _row_to_experience(self, row: Any) -> ExperienceRecord:
        res_parts = str(row["resolution"]).split("x")
        res_tuple = (int(res_parts[0]), int(res_parts[1])) if len(res_parts) == 2 else (16, 16)
        keys = row.keys()
        return ExperienceRecord(
            id=row["id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            task_category=row["task_category"],
            asset_category=row["asset_category"],
            resolution=res_tuple,
            art_profile=json.loads(row["art_profile"]),
            tools_used=json.loads(row["tools_used"]),
            input_context=json.loads(row["input_context"]),
            output_summary=json.loads(row["output_summary"]),
            execution_time_ms=float(row["execution_time_ms"]),
            execution_outcome=row["execution_outcome"] if "execution_outcome" in keys and row["execution_outcome"] else "SUCCESS",
            validation_outcome=row["validation_outcome"] if "validation_outcome" in keys and row["validation_outcome"] else "SKIPPED",
            qa_outcome=row["qa_outcome"] if "qa_outcome" in keys and row["qa_outcome"] else "SKIPPED",
            human_acceptance=row["human_acceptance"] if "human_acceptance" in keys else None,
            outcome=OutcomeType(row["outcome"]),
            qa_report=json.loads(row["qa_report"]) if row["qa_report"] else None,
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # -------------------------------------------------------------------------
    # Feedback Operations
    # -------------------------------------------------------------------------
    def save_feedback(self, record: FeedbackRecord) -> FeedbackRecord:
        """Saves a FeedbackRecord. Enforces FK constraint to experience."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO feedbacks (
                    id, experience_id, project_id, feedback_type, user_rating,
                    notes, suggested_changes, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    experience_id=excluded.experience_id,
                    project_id=excluded.project_id,
                    feedback_type=excluded.feedback_type,
                    user_rating=excluded.user_rating,
                    notes=excluded.notes,
                    suggested_changes=excluded.suggested_changes,
                    idempotency_key=excluded.idempotency_key,
                    created_at=excluded.created_at
                """,
                (
                    record.id,
                    record.experience_id,
                    record.project_id,
                    record.feedback_type.value if isinstance(record.feedback_type, FeedbackType) else str(record.feedback_type),
                    record.user_rating,
                    record.notes,
                    json.dumps(record.suggested_changes),
                    record.idempotency_key,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def get_feedbacks_for_experience(self, exp_id: str) -> List[FeedbackRecord]:
        """Retrieves all feedback records for a given experience."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM feedbacks WHERE experience_id = ? ORDER BY created_at ASC",
            (exp_id,),
        ).fetchall()
        return [self._row_to_feedback(r) for r in rows]

    def get_feedback_by_idempotency_key(self, key: str) -> Optional[FeedbackRecord]:
        """Retrieves a feedback record by its unique idempotency key."""
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM feedbacks WHERE idempotency_key = ?", (key,)).fetchone()
        if not row:
            return None
        return self._row_to_feedback(row)

    def _row_to_feedback(self, r: Any) -> FeedbackRecord:
        keys = r.keys()
        return FeedbackRecord(
            id=r["id"],
            experience_id=r["experience_id"],
            project_id=r["project_id"],
            feedback_type=FeedbackType(r["feedback_type"]),
            user_rating=float(r["user_rating"]) if r["user_rating"] is not None else None,
            notes=r["notes"],
            suggested_changes=json.loads(r["suggested_changes"]),
            idempotency_key=r["idempotency_key"] if "idempotency_key" in keys else None,
            created_at=datetime.fromisoformat(r["created_at"]),
        )

    # -------------------------------------------------------------------------
    # Knowledge Operations
    # -------------------------------------------------------------------------
    def save_knowledge(self, record: KnowledgeRecord) -> KnowledgeRecord:
        """Saves or updates a KnowledgeRecord, enforcing strict data ownership across knowledge tiers."""
        # Objective C Data Ownership Safeguard:
        # KnowledgeRecord belongs to the Knowledge Repository.
        # Feedback entities must be recorded independently in the Feedback Repository via save_feedback.
        # Validated skills must be stored as versioned SkillDefinition JSON manifests in the Skill Registry.
        if record.knowledge_type == KnowledgeType.HUMAN_FEEDBACK:
            if not record.applied_feedback_ids and not record.source_experience_ids:
                raise ValueError(
                    "HUMAN_FEEDBACK knowledge tier requires linked feedback/experience IDs. "
                    "Raw human feedback must be recorded via save_feedback() into the feedback repository."
                )
        elif record.knowledge_type == KnowledgeType.VALIDATED_SKILL:
            if "skill_id" not in record.conditions and not record.source_experience_ids:
                raise ValueError(
                    "VALIDATED_SKILL knowledge tier requires linked skill definition ID or experience IDs. "
                    "Skill workflows must be registered as versioned SkillDefinition files in SkillRegistry."
                )

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO knowledge (
                    id, project_id, category, rule_name, description,
                    conditions, recommendations, confidence_score,
                    source_experience_ids, applied_feedback_ids,
                    knowledge_type, evidence_status, provenance,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id=excluded.project_id,
                    category=excluded.category,
                    rule_name=excluded.rule_name,
                    description=excluded.description,
                    conditions=excluded.conditions,
                    recommendations=excluded.recommendations,
                    confidence_score=excluded.confidence_score,
                    source_experience_ids=excluded.source_experience_ids,
                    applied_feedback_ids=excluded.applied_feedback_ids,
                    knowledge_type=excluded.knowledge_type,
                    evidence_status=excluded.evidence_status,
                    provenance=excluded.provenance,
                    updated_at=excluded.updated_at
                """,
                (
                    record.id,
                    record.project_id,
                    record.category.value if isinstance(record.category, KnowledgeCategory) else str(record.category),
                    record.rule_name,
                    record.description,
                    json.dumps(record.conditions),
                    json.dumps(record.recommendations),
                    record.confidence_score,
                    json.dumps(record.source_experience_ids),
                    json.dumps(record.applied_feedback_ids),
                    record.knowledge_type.value if hasattr(record.knowledge_type, "value") else str(record.knowledge_type),
                    record.evidence_status.value if hasattr(record.evidence_status, "value") else str(record.evidence_status),
                    record.provenance.model_dump_json() if record.provenance else None,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
        return record

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        """Retrieves a KnowledgeRecord by ID."""
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (knowledge_id,)).fetchone()
        if not row:
            return None
        return self._row_to_knowledge(row)

    def query_knowledge(
        self,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        knowledge_type: Optional[Any] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[KnowledgeRecord]:
        """
        Queries knowledge with strict project isolation and universal Art Bible rule inclusion.
        If project_id is given: returns rules where (project_id = ? OR project_id IS NULL).
        If project_id is None: returns only universal rules (project_id IS NULL).
        """
        clauses: List[str] = []
        params: List[Any] = []

        if min_confidence > 0.0:
            clauses.append("(confidence_score >= ? OR confidence_score IS NULL)")
            params.append(min_confidence)

        if project_id is not None:
            clauses.append("(project_id = ? OR project_id IS NULL)")
            params.append(project_id)
        else:
            clauses.append("project_id IS NULL")

        if category is not None:
            cat_str = category.value if isinstance(category, KnowledgeCategory) else str(category)
            clauses.append("category = ?")
            params.append(cat_str)

        if knowledge_type is not None:
            kt_str = knowledge_type.value if hasattr(knowledge_type, "value") else str(knowledge_type)
            clauses.append("knowledge_type = ?")
            params.append(kt_str)

        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM knowledge {where_str} ORDER BY (CASE WHEN confidence_score IS NOT NULL THEN confidence_score ELSE 1.0 END) DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        conn = self.db.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_knowledge(r) for r in rows]

    def delete_knowledge(self, knowledge_id: str) -> bool:
        """Deletes a KnowledgeRecord."""
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM knowledge WHERE id = ?", (knowledge_id,))
            return cur.rowcount > 0

    def _row_to_knowledge(self, row: Any) -> KnowledgeRecord:
        keys = row.keys()
        applied_feedbacks = []
        if "applied_feedback_ids" in keys and row["applied_feedback_ids"]:
            try:
                applied_feedbacks = json.loads(row["applied_feedback_ids"])
            except Exception:
                applied_feedbacks = []

        from libresprite_game_mcp.learning.models import (
            EvidenceStatus,
            KnowledgeType,
            ReferenceProvenance,
        )

        kt = KnowledgeType.EMPIRICAL_KNOWLEDGE
        if "knowledge_type" in keys and row["knowledge_type"]:
            try:
                kt = KnowledgeType(row["knowledge_type"])
            except Exception:
                kt = KnowledgeType.EMPIRICAL_KNOWLEDGE

        ev = EvidenceStatus.EMPIRICAL_OBSERVATION
        if "evidence_status" in keys and row["evidence_status"]:
            try:
                ev = EvidenceStatus(row["evidence_status"])
            except Exception:
                ev = EvidenceStatus.EMPIRICAL_OBSERVATION

        prov = None
        if "provenance" in keys and row["provenance"]:
            try:
                prov = ReferenceProvenance.model_validate_json(row["provenance"])
            except Exception:
                prov = None

        conf = float(row["confidence_score"]) if row["confidence_score"] is not None else None

        return KnowledgeRecord(
            id=row["id"],
            project_id=row["project_id"],
            knowledge_type=kt,
            evidence_status=ev,
            category=KnowledgeCategory(row["category"]),
            rule_name=row["rule_name"],
            description=row["description"],
            conditions=json.loads(row["conditions"]),
            recommendations=json.loads(row["recommendations"]),
            confidence_score=conf,
            provenance=prov,
            source_experience_ids=json.loads(row["source_experience_ids"]),
            applied_feedback_ids=applied_feedbacks,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
