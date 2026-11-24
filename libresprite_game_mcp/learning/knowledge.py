"""
Knowledge Management and Retrieval.
Manages rule lifecycle, confidence scoring, evidence tracking, and context-aware retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from libresprite_game_mcp.learning.models import (
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    OutcomeType,
)
from libresprite_game_mcp.learning.repository import LearningRepository


class KnowledgeManager:
    """Manages knowledge records, evidence updates, and automated rule synthesis."""

    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def add_rule(
        self,
        rule_name: str,
        category: KnowledgeCategory,
        description: str,
        conditions: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        initial_confidence: float = 0.5,
        source_experience_ids: Optional[List[str]] = None,
    ) -> KnowledgeRecord:
        """Creates and stores a new knowledge rule."""
        record = KnowledgeRecord(
            project_id=project_id,
            category=category,
            rule_name=rule_name,
            description=description,
            conditions=conditions or {},
            recommendations=recommendations or {},
            confidence_score=max(0.0, min(1.0, initial_confidence)),
            source_experience_ids=source_experience_ids or [],
        )
        return self.repository.save_knowledge(record)

    def update_confidence(
        self,
        knowledge_id: str,
        outcome: OutcomeType,
        feedback: Optional[FeedbackRecord] = None,
        experience_id: Optional[str] = None,
    ) -> KnowledgeRecord:
        """
        Adjusts rule confidence based on empirical outcomes and human feedback.
        """
        rule = self.repository.get_knowledge(knowledge_id)
        if not rule:
            raise ValueError(f"Knowledge rule '{knowledge_id}' not found.")

        delta = 0.0
        # 1. Outcome delta
        if outcome == OutcomeType.SUCCESS:
            delta += 0.05
        elif outcome == OutcomeType.FAILURE:
            delta -= 0.15

        # 2. Feedback delta
        if feedback:
            # Idempotency check: do not apply the same feedback record twice
            if feedback.id in rule.applied_feedback_ids:
                return rule
            rule.applied_feedback_ids.append(feedback.id)

            if feedback.feedback_type == FeedbackType.APPROVAL:
                delta += 0.10
            elif feedback.feedback_type == FeedbackType.REJECTION:
                delta -= 0.20
            elif feedback.feedback_type == FeedbackType.CORRECTION:
                delta -= 0.05

            if feedback.user_rating is not None:
                if feedback.user_rating >= 4.0:
                    delta += 0.05
                elif feedback.user_rating <= 2.0:
                    delta -= 0.10

        new_score = round(max(0.0, min(1.0, rule.confidence_score + delta)), 3)
        rule.confidence_score = new_score
        rule.updated_at = datetime.now(timezone.utc)

        if experience_id and experience_id not in rule.source_experience_ids:
            rule.source_experience_ids.append(experience_id)

        return self.repository.save_knowledge(rule)

    def synthesize_from_experiences(
        self,
        task_category: str,
        min_occurrences: int = 2,
        project_id: Optional[str] = None,
    ) -> List[KnowledgeRecord]:
        """
        Analyzes successful experiences and synthesizes common constraints into knowledge rules.
        """
        experiences = self.repository.query_experiences(
            project_id=project_id,
            task_category=task_category,
            outcome=OutcomeType.SUCCESS.value,
            limit=100,
        )

        if len(experiences) < min_occurrences:
            return []

        synthesized_rules: List[KnowledgeRecord] = []

        # Analyze palette stability
        palette_counts: Dict[str, int] = {}
        source_exp_ids: List[str] = []
        for exp in experiences:
            palette = exp.art_profile.get("palette_name")
            if palette:
                palette_counts[palette] = palette_counts.get(palette, 0) + 1
                source_exp_ids.append(exp.id)

        for palette, count in palette_counts.items():
            if count >= min_occurrences:
                rule_name = f"Standard {palette.upper()} Palette for {task_category.capitalize()}"
                rule = self.add_rule(
                    rule_name=rule_name,
                    category=KnowledgeCategory.PALETTE,
                    description=f"Empirically validated consistent palette '{palette}' for {task_category}",
                    conditions={"task_category": task_category},
                    recommendations={"recommended_palette": palette},
                    project_id=project_id,
                    initial_confidence=round(min(0.9, 0.5 + (count * 0.1)), 2),
                    source_experience_ids=source_exp_ids,
                )
                synthesized_rules.append(rule)

        return synthesized_rules


class KnowledgeRetriever:
    """Retrieves and packages applicable knowledge for agents and generators."""

    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def retrieve_applicable_rules(
        self,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
        category: Optional[KnowledgeCategory] = None,
        resolution: Optional[Tuple[int, int]] = None,
        min_confidence: float = 0.3,
    ) -> List[KnowledgeRecord]:
        """
        Retrieves matching knowledge rules.
        Enforces project isolation: retrieves universal rules plus matching project_id rules.
        Filters rules by context conditions.
        """
        all_candidates = self.repository.query_knowledge(
            project_id=project_id,
            category=category,
            min_confidence=min_confidence,
            limit=100,
        )

        matched: List[KnowledgeRecord] = []
        for rule in all_candidates:
            conds = rule.conditions

            # Category filter
            if "task_category" in conds and task_category:
                if conds["task_category"].lower() != task_category.lower():
                    continue

            # Resolution filter
            if "resolution" in conds and resolution:
                expected_res = conds["resolution"]
                actual_res = f"{resolution[0]}x{resolution[1]}"
                if expected_res != actual_res and expected_res != list(resolution):
                    continue

            matched.append(rule)

        # Sort: Highest confidence first; if tied, project-specific rules take precedence over universal
        matched.sort(
            key=lambda r: (r.confidence_score, 1 if r.project_id is not None else 0),
            reverse=True,
        )
        return matched

    def format_guidance(self, rules: List[KnowledgeRecord]) -> Dict[str, Any]:
        """Consolidates retrieved rules into structured guidance for generators/prompts."""
        guidance: Dict[str, Any] = {
            "palettes": [],
            "outlines": [],
            "constraints": [],
            "recommendations": {},
        }

        for rule in rules:
            recs = rule.recommendations
            if "recommended_palette" in recs:
                guidance["palettes"].append(recs["recommended_palette"])
            if "outline_mode" in recs:
                guidance["outlines"].append(recs["outline_mode"])

            guidance["constraints"].append({
                "rule": rule.rule_name,
                "confidence": rule.confidence_score,
                "category": rule.category.value,
                "details": recs,
            })
            for k, v in recs.items():
                if k not in guidance["recommendations"]:
                    guidance["recommendations"][k] = v

        return guidance
