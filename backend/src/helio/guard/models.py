SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS guard_events (
    trade_intent_id TEXT PRIMARY KEY,
    thesis_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    decision TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    trade_intent_json TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    logged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_guard_events_thesis ON guard_events(thesis_id);
CREATE INDEX IF NOT EXISTS idx_guard_events_symbol ON guard_events(symbol);
CREATE INDEX IF NOT EXISTS idx_guard_events_logged_at ON guard_events(logged_at);
"""
