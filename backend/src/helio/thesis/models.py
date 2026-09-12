SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS thesis_events (
    decision_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    regime TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    valid INTEGER NOT NULL,
    prepared_state_json TEXT NOT NULL,
    thesis_json TEXT NOT NULL,
    validation_json TEXT NOT NULL,
    logged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_thesis_events_symbol ON thesis_events(symbol);
CREATE INDEX IF NOT EXISTS idx_thesis_events_logged_at ON thesis_events(logged_at);
"""
