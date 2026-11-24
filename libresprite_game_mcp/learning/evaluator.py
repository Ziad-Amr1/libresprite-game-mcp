"""
Outcome Evaluator.
Computes objective task quality scores and outcome statuses from QA audits, runtime errors, and user feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from libresprite_game_mcp.learning.models import FeedbackRecord, FeedbackType, OutcomeType


class OutcomeEvaluator:
    """Evaluates asset quality and execution success."""

    def evaluate(
        self,
        qa_report: Optional[Dict[str, Any]] = None,
        execution_error: Optional[str] = None,
        feedback: Optional[FeedbackRecord] = None,
    ) -> Tuple[OutcomeType, float, List[str]]:
        """
        Calculates outcome status, quality score [0.0 - 1.0], and diagnostic notes.
        """
        notes: List[str] = []

        # 1. Check runtime execution error
        if execution_error:
            notes.append(f"Runtime execution failure: {execution_error}")
            return OutcomeType.FAILURE, 0.0, notes

        # 2. Evaluate QA Report if provided
        base_score = 1.0
        has_critical_errors = False

        if qa_report:
            passed = qa_report.get("passed", True)
            critical_errors = qa_report.get("critical_errors", [])
            warnings = qa_report.get("warnings", [])

            if critical_errors:
                has_critical_errors = True
                notes.append(f"QA Critical Errors: {len(critical_errors)}")
                base_score -= 0.3 * len(critical_errors)

            if warnings:
                notes.append(f"QA Warnings: {len(warnings)}")
                base_score -= 0.1 * len(warnings)

            if not passed or has_critical_errors:
                base_score = min(base_score, 0.3)

        base_score = max(0.0, min(1.0, base_score))

        # 3. Incorporate User Feedback if available
        if feedback:
            if feedback.feedback_type == FeedbackType.REJECTION:
                base_score = max(0.0, base_score - 0.4)
                notes.append(f"User rejected: {feedback.notes or 'No reason provided'}")
            elif feedback.feedback_type == FeedbackType.APPROVAL:
                base_score = min(1.0, base_score + 0.2)
                notes.append("User approved asset")
            elif feedback.feedback_type == FeedbackType.CORRECTION:
                base_score = max(0.2, min(0.6, base_score))
                notes.append("User requested corrections")

            if feedback.user_rating is not None:
                normalized_rating = feedback.user_rating / 5.0
                base_score = round(0.5 * base_score + 0.5 * normalized_rating, 3)

        base_score = max(0.0, min(1.0, round(base_score, 3)))

        # 4. Map final score to OutcomeType
        if has_critical_errors or (feedback and feedback.feedback_type == FeedbackType.REJECTION):
            outcome = OutcomeType.FAILURE
        elif base_score >= 0.8:
            outcome = OutcomeType.SUCCESS
        elif base_score >= 0.4:
            outcome = OutcomeType.PARTIAL
        else:
            outcome = OutcomeType.FAILURE

        return outcome, base_score, notes
