SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversation_events (
    request_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    message TEXT NOT NULL,
    intent TEXT NOT NULL,
    risk_profile TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    response_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_conversation_events_status ON conversation_events(status);
CREATE INDEX IF NOT EXISTS idx_conversation_events_conversation_id ON conversation_events(conversation_id);
"""
