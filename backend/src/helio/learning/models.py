SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS learning_events (
    event_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    decision_json TEXT,
    execution_result_json TEXT,
    outcome_json TEXT,
    logged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learning_events_strategy ON learning_events(strategy_id);
CREATE INDEX IF NOT EXISTS idx_learning_events_intent ON learning_events(intent_id);
"""
