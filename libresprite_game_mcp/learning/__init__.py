"""
Learning Layer module.
Captures experiences, user feedback, evaluates outcomes, and manages structured knowledge.
"""

from libresprite_game_mcp.learning.collector import ExperienceCollector, FeedbackCollector
from libresprite_game_mcp.learning.evaluator import OutcomeEvaluator
from libresprite_game_mcp.learning.knowledge import KnowledgeManager, KnowledgeRetriever
from libresprite_game_mcp.learning.models import (
    CharacterGenerationGuidance,
    EvidenceStatus,
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
    OutcomeType,
    ReferenceProvenance,
)
from libresprite_game_mcp.learning.normalizer import ExperienceNormalizer
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.learning.seed_knowledge import (
    get_pixel_art_knowledge_rules,
    seed_art_bible_knowledge,
)

__all__ = [
    "CharacterGenerationGuidance",
    "EvidenceStatus",
    "ExperienceCollector",
    "ExperienceNormalizer",
    "ExperienceRecord",
    "FeedbackCollector",
    "FeedbackRecord",
    "FeedbackType",
    "KnowledgeCategory",
    "KnowledgeManager",
    "KnowledgeRecord",
    "KnowledgeRepository",
    "KnowledgeRetriever",
    "KnowledgeType",
    "LearningRepository",
    "OutcomeEvaluator",
    "OutcomeType",
    "ReferenceProvenance",
    "get_pixel_art_knowledge_rules",
    "seed_art_bible_knowledge",
]
