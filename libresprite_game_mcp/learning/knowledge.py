"""
Knowledge Management and Retrieval.
Manages rule lifecycle, confidence scoring, evidence tracking, and context-aware retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from libresprite_game_mcp.learning.models import (
    EvidenceStatus,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
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
        Protected: EXTERNAL_REFERENCE records are immutable and cannot be altered by feedback.
        """
        rule = self.repository.get_knowledge(knowledge_id)
        if not rule:
            raise ValueError(f"Knowledge rule '{knowledge_id}' not found.")

        # External reference protection: literature citations must not be modified by empirical feedback
        if rule.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE:
            return rule

        base_score = rule.confidence_score if rule.confidence_score is not None else 0.5
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

        new_score = round(max(0.0, min(1.0, base_score + delta)), 3)
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
        palette_name: Optional[str] = None,
        art_profile: Optional[str] = None,
        archetype: Optional[str] = None,
        animation_state: Optional[str] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        min_confidence: float = 0.0,
    ) -> List[KnowledgeRecord]:
        """
        Retrieves matching knowledge rules with conditional applicability filtering.
        Enforces project isolation: retrieves universal rules plus matching project_id rules.
        Filters rules strictly by context conditions (resolution, palette, archetype, animation state).
        """
        all_candidates = self.repository.query_knowledge(
            project_id=project_id,
            category=category,
            knowledge_type=knowledge_type,
            min_confidence=min_confidence,
            limit=100,
        )

        matched: List[KnowledgeRecord] = []
        for rule in all_candidates:
            conds = rule.conditions
            prov = rule.provenance

            # 1. Category filter (conditions + ReferenceProvenance.applicable_asset_categories)
            if task_category:
                cat_lower = task_category.lower().strip()
                if "task_category" in conds:
                    if conds["task_category"].lower().strip() != cat_lower:
                        continue
                if prov and prov.applicable_asset_categories:
                    allowed_cats = [c.lower().strip() for c in prov.applicable_asset_categories]
                    if "all" not in allowed_cats and cat_lower not in allowed_cats:
                        continue

            # 2. Resolution filter (conditions + ReferenceProvenance.applicable_resolutions)
            if resolution:
                actual_res_str = f"{resolution[0]}x{resolution[1]}"
                if "resolution" in conds:
                    expected_res = conds["resolution"]
                    if isinstance(expected_res, list):
                        if actual_res_str not in expected_res and list(resolution) != expected_res:
                            continue
                    elif expected_res != actual_res_str and expected_res != list(resolution):
                        continue
                if prov and prov.applicable_resolutions:
                    allowed_res = [r.lower().strip() for r in prov.applicable_resolutions]
                    if "all" not in allowed_res and actual_res_str not in allowed_res:
                        continue

            # 3. Palette condition filter
            if palette_name:
                pal_lower = palette_name.lower().strip()
                if "palette_name" in conds:
                    rule_pal = conds["palette_name"]
                    if isinstance(rule_pal, list):
                        if pal_lower not in [p.lower().strip() for p in rule_pal]:
                            continue
                    elif str(rule_pal).lower().strip() != pal_lower:
                        continue
                if "palettes" in conds:
                    rule_pals = conds["palettes"]
                    if isinstance(rule_pals, list) and pal_lower not in [p.lower().strip() for p in rule_pals]:
                        continue

            # 4. Art Profile & Style filter (conditions + ReferenceProvenance.applicable_styles)
            if art_profile:
                prof_lower = art_profile.lower().strip()
                if "art_profile" in conds and conds["art_profile"].lower().strip() != prof_lower:
                    continue
                if "style" in conds and conds["style"].lower().strip() != prof_lower:
                    continue
                if prov and prov.applicable_styles:
                    allowed_styles = [s.lower().strip() for s in prov.applicable_styles]
                    if "all" not in allowed_styles:
                        incompatible_styles = (
                            "vector", "modern_vector_ui", "vector_ui", "3d", "realistic",
                            "photorealistic", "low_poly", "voxel", "high_res_ui"
                        )
                        is_incompatible = any(inc in prof_lower for inc in incompatible_styles)
                        if is_incompatible:
                            continue

            # 5. Archetype condition filter
            if archetype:
                arch_lower = archetype.lower().strip()
                if "archetype" in conds:
                    rule_arch = conds["archetype"]
                    if isinstance(rule_arch, list):
                        if arch_lower not in [a.lower().strip() for a in rule_arch]:
                            continue
                    elif str(rule_arch).lower().strip() != arch_lower:
                        continue

            # 6. Animation state filter
            if animation_state:
                state_lower = animation_state.lower().strip()
                if "animation_state" in conds:
                    rule_state = conds["animation_state"]
                    if isinstance(rule_state, list):
                        if state_lower not in [s.lower().strip() for s in rule_state]:
                            continue
                    elif str(rule_state).lower().strip() != state_lower:
                        continue

            matched.append(rule)

        # Sort: Explicit Evidence Priority Ordering (Objective 5: No artificial 0.95 or 1.0 fallbacks)
        EVIDENCE_PRIORITY = {
            EvidenceStatus.HUMAN_DIRECTIVE: 4,
            EvidenceStatus.COMMUNITY_CONSENSUS: 3,
            EvidenceStatus.REFERENCE_GUIDANCE: 2,
            EvidenceStatus.EMPIRICAL_OBSERVATION: 1,
        }

        def _sort_key(r: KnowledgeRecord) -> Tuple[int, int, float]:
            is_proj = 1 if r.project_id is not None else 0
            ev_priority = EVIDENCE_PRIORITY.get(r.evidence_status, 0)
            emp_conf = r.confidence_score if r.confidence_score is not None else 0.0
            return (is_proj, ev_priority, emp_conf)

        matched.sort(key=_sort_key, reverse=True)
        return matched

    def format_guidance(self, rules: List[KnowledgeRecord]) -> Dict[str, Any]:
        """Consolidates retrieved rules into structured guidance for generators and specialist agents."""
        guidance: Dict[str, Any] = {
            "palettes": [],
            "outlines": [],
            "silhouette_recommendations": {},
            "shading_recommendations": {},
            "outline_recommendations": {},
            "animation_requirements": {},
            "constraints": [],
            "recommendations": {},
            "applicable_rules": [],
            "evidence_statuses": {},
        }

        for rule in rules:
            recs = rule.recommendations
            guidance["applicable_rules"].append(rule.rule_name)
            guidance["evidence_statuses"][rule.rule_name] = rule.evidence_status.value

            if "recommended_palette" in recs and recs["recommended_palette"] not in guidance["palettes"]:
                guidance["palettes"].append(recs["recommended_palette"])
            if "outline_mode" in recs and recs["outline_mode"] not in guidance["outlines"]:
                guidance["outlines"].append(recs["outline_mode"])

            # Category-specific guidance mapping
            if rule.category == KnowledgeCategory.SILHOUETTE:
                guidance["silhouette_recommendations"].update(recs)
            elif rule.category == KnowledgeCategory.LIGHTING:
                guidance["shading_recommendations"].update(recs)
            elif rule.category == KnowledgeCategory.OUTLINE:
                guidance["outline_recommendations"].update(recs)
            elif rule.category == KnowledgeCategory.ANIMATION_TIMING:
                guidance["animation_requirements"].update(recs)

            guidance["constraints"].append({
                "rule": rule.rule_name,
                "confidence": rule.confidence_score,
                "evidence_status": rule.evidence_status.value,
                "knowledge_type": rule.knowledge_type.value,
                "category": rule.category.value,
                "details": recs,
            })
            for k, v in recs.items():
                if k not in guidance["recommendations"]:
                    guidance["recommendations"][k] = v

        guidance["rule_metadata"] = {
            rule.rule_name: {
                "id": rule.id,
                "knowledge_type": rule.knowledge_type.value,
                "evidence_status": rule.evidence_status.value,
                "category": rule.category.value,
                "provenance": rule.provenance.model_dump() if rule.provenance else None,
            }
            for rule in rules
        }

        return guidance
