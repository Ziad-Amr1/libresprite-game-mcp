-- 001_initial.sql
-- Initial schema for LibreSprite Learning Layer & Skill Builder

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS experiences (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_category TEXT NOT NULL,
    asset_category TEXT NOT NULL,
    resolution TEXT NOT NULL,
    art_profile TEXT NOT NULL,
    tools_used TEXT NOT NULL,
    input_context TEXT NOT NULL,
    output_summary TEXT NOT NULL,
    execution_time_ms REAL NOT NULL,
    outcome TEXT NOT NULL,
    qa_report TEXT,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiences_project_id ON experiences(project_id);
CREATE INDEX IF NOT EXISTS idx_experiences_task_category ON experiences(task_category);
CREATE INDEX IF NOT EXISTS idx_experiences_outcome ON experiences(outcome);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at);

CREATE TABLE IF NOT EXISTS feedbacks (
    id TEXT PRIMARY KEY,
    experience_id TEXT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    user_rating REAL,
    notes TEXT,
    suggested_changes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedbacks_experience_id ON feedbacks(experience_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_project_id ON feedbacks(project_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_feedback_type ON feedbacks(feedback_type);

CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    category TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    description TEXT NOT NULL,
    conditions TEXT NOT NULL,
    recommendations TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    source_experience_ids TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_project_id ON knowledge(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_confidence ON knowledge(confidence_score);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_versions (
    skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    trigger_conditions TEXT NOT NULL,
    required_tools TEXT NOT NULL,
    parameters_schema TEXT NOT NULL,
    workflow TEXT NOT NULL,
    validation_rules TEXT NOT NULL,
    art_profile_compatibility TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (skill_id, version)
);

CREATE INDEX IF NOT EXISTS idx_skill_versions_status ON skill_versions(status);

CREATE TABLE IF NOT EXISTS skill_executions (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    project_id TEXT NOT NULL,
    execution_context TEXT NOT NULL,
    status TEXT NOT NULL,
    outputs TEXT NOT NULL,
    qa_passed INTEGER NOT NULL,
    execution_duration_ms REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_executions_skill ON skill_executions(skill_id, skill_version);
CREATE INDEX IF NOT EXISTS idx_skill_executions_project ON skill_executions(project_id);

CREATE TABLE IF NOT EXISTS skill_evaluations (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    test_cases_run INTEGER NOT NULL,
    test_cases_passed INTEGER NOT NULL,
    score REAL NOT NULL,
    evaluation_summary TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_evaluations_skill ON skill_evaluations(skill_id, skill_version);

CREATE TABLE IF NOT EXISTS skill_approvals (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    action TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    comments TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_approvals_skill ON skill_approvals(skill_id, skill_version);
