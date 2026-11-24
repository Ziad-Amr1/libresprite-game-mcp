-- 003_provenance_and_knowledge_types.sql
-- Separate knowledge types (EXTERNAL_REFERENCE, EMPIRICAL_KNOWLEDGE, HUMAN_FEEDBACK, VALIDATED_SKILL)
-- Make confidence_score nullable (external references do not use pseudo-probabilities)
-- Add structured provenance and evidence tracking

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS knowledge_new (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    category TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    description TEXT NOT NULL,
    conditions TEXT NOT NULL,
    recommendations TEXT NOT NULL,
    confidence_score REAL,
    source_experience_ids TEXT NOT NULL,
    applied_feedback_ids TEXT DEFAULT '[]',
    knowledge_type TEXT DEFAULT 'EMPIRICAL_KNOWLEDGE',
    evidence_status TEXT DEFAULT 'EMPIRICAL_OBSERVATION',
    provenance TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO knowledge_new (
    id, project_id, category, rule_name, description,
    conditions, recommendations, confidence_score,
    source_experience_ids, applied_feedback_ids,
    knowledge_type, evidence_status, provenance,
    created_at, updated_at
)
SELECT 
    id, project_id, category, rule_name, description,
    conditions, recommendations, confidence_score,
    source_experience_ids, COALESCE(applied_feedback_ids, '[]'),
    'EMPIRICAL_KNOWLEDGE', 'EMPIRICAL_OBSERVATION', NULL,
    created_at, updated_at
FROM knowledge;

DROP TABLE knowledge;

ALTER TABLE knowledge_new RENAME TO knowledge;

CREATE INDEX IF NOT EXISTS idx_knowledge_project_id ON knowledge(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_confidence ON knowledge(confidence_score);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge(knowledge_type);

PRAGMA foreign_keys = ON;
