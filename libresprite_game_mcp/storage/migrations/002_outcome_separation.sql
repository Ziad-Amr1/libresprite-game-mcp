-- 002_outcome_separation.sql
-- Add separated outcome fields and idempotency tracking

ALTER TABLE experiences ADD COLUMN execution_outcome TEXT DEFAULT 'SUCCESS';
ALTER TABLE experiences ADD COLUMN validation_outcome TEXT DEFAULT 'SKIPPED';
ALTER TABLE experiences ADD COLUMN qa_outcome TEXT DEFAULT 'SKIPPED';
ALTER TABLE experiences ADD COLUMN human_acceptance TEXT;

ALTER TABLE feedbacks ADD COLUMN idempotency_key TEXT;
CREATE INDEX IF NOT EXISTS idx_feedbacks_idempotency ON feedbacks(idempotency_key);

ALTER TABLE knowledge ADD COLUMN applied_feedback_ids TEXT DEFAULT '[]';
