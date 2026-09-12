SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS execution_events (
    execution_id TEXT PRIMARY KEY,
    trade_intent_id TEXT NOT NULL UNIQUE,
    thesis_id TEXT NOT NULL,
    status TEXT,
    lifecycle_json TEXT NOT NULL,
    authorized_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_execution_events_thesis ON execution_events(thesis_id);
CREATE INDEX IF NOT EXISTS idx_execution_events_authorized_at ON execution_events(authorized_at);
"""
