"""
Experience and Feedback Collectors.
Gathers execution results, normalizes inputs, evaluates quality, and records feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from libresprite_game_mcp.learning.evaluator import OutcomeEvaluator
from libresprite_game_mcp.learning.models import (
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    OutcomeType,
)
from libresprite_game_mcp.learning.normalizer import ExperienceNormalizer
from libresprite_game_mcp.learning.repository import LearningRepository


class ExperienceCollector:
    """Collects, cleanses, evaluates, and stores production experiences."""

    def __init__(
        self,
        repository: LearningRepository,
        normalizer: Optional[ExperienceNormalizer] = None,
        evaluator: Optional[OutcomeEvaluator] = None,
    ):
        self.repository = repository
        self.normalizer = normalizer or ExperienceNormalizer()
        self.evaluator = evaluator or OutcomeEvaluator()

    def record_task_run(
        self,
        task_id: str,
        task_category: str,
        asset_category: str = "sprite",
        resolution: Optional[Tuple[int, int]] = None,
        input_context: Optional[Dict[str, Any]] = None,
        output_summary: Optional[Dict[str, Any]] = None,
        tools_used: Optional[List[str]] = None,
        execution_time_ms: float = 0.0,
        execution_outcome: str = "SUCCESS",
        validation_outcome: str = "SKIPPED",
        qa_outcome: str = "SKIPPED",
        human_acceptance: Optional[str] = None,
        qa_report: Optional[Dict[str, Any]] = None,
        art_profile: Optional[Dict[str, Any]] = None,
        project_id: str = "default",
        execution_error: Optional[str] = None,
        explicit_outcome: Optional[OutcomeType] = None,
    ) -> ExperienceRecord:
        """Captures a complete execution task run with separated outcome dimensions."""
        clean_context = self.normalizer.sanitize_payload(input_context or {})
        clean_output = self.normalizer.sanitize_payload(output_summary or {})
        clean_profile = self.normalizer.sanitize_payload(art_profile or {})

        res = resolution or self.normalizer.extract_resolution(clean_context)
        tags = self.normalizer.extract_tags(
            task_category=task_category,
            asset_category=asset_category,
            resolution=res,
            art_profile=clean_profile,
            context=clean_context,
        )

        if explicit_outcome is not None:
            outcome = explicit_outcome
        else:
            outcome, _score, _notes = self.evaluator.evaluate(
                qa_report=qa_report,
                execution_error=execution_error,
            )

        # Infer outcomes if default
        resolved_exec_outcome = "FAILED" if (execution_error or outcome == OutcomeType.FAILURE and not qa_report) else execution_outcome
        resolved_qa_outcome = qa_outcome
        if qa_report:
            if not qa_report.get("passed", True):
                resolved_qa_outcome = "CRITICAL_FAIL" if qa_report.get("critical_errors") else "FAILED"
            else:
                resolved_qa_outcome = "WARNINGS" if qa_report.get("warnings") else "PASSED"

        record = ExperienceRecord(
            project_id=project_id,
            task_id=task_id,
            task_category=task_category,
            asset_category=asset_category,
            resolution=res,
            art_profile=clean_profile,
            tools_used=tools_used or [],
            input_context=clean_context,
            output_summary=clean_output,
            execution_time_ms=execution_time_ms,
            execution_outcome=resolved_exec_outcome,
            validation_outcome=validation_outcome,
            qa_outcome=resolved_qa_outcome,
            human_acceptance=human_acceptance,
            outcome=outcome,
            qa_report=qa_report,
            tags=tags,
        )

        return self.repository.save_experience(record)


class FeedbackCollector:
    """Collects and stores user feedback, associating it with target experiences."""

    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def record_feedback(
        self,
        experience_id: str,
        feedback_type: FeedbackType,
        user_rating: Optional[float] = None,
        notes: Optional[str] = None,
        suggested_changes: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> FeedbackRecord:
        """Records user feedback for an existing experience with idempotency protection."""
        # 1. Idempotency check
        if idempotency_key:
            existing = self.repository.get_feedback_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        experience = self.repository.get_experience(experience_id)
        if not experience:
            raise ValueError(f"Experience '{experience_id}' not found.")

        resolved_project_id = project_id or experience.project_id

        record = FeedbackRecord(
            experience_id=experience_id,
            project_id=resolved_project_id,
            feedback_type=feedback_type,
            user_rating=user_rating,
            notes=notes,
            suggested_changes=suggested_changes or {},
            idempotency_key=idempotency_key,
        )

        saved = self.repository.save_feedback(record)

        # Update experience human_acceptance status
        experience.human_acceptance = feedback_type.value.upper()
        self.repository.save_experience(experience)

        return saved
