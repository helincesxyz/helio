// Mirrors backend/src/helio/schemas/*.py — kept in sync manually for v1.
// See docs/SCHEMAS.md for the canonical definitions.

export type Mode = "simulation" | "live";

export interface TradeIntent {
  intent_id: string;
  created_at: string;
  strategy_id: string;
  symbol: string;
  instrument_type: "SPOT" | "SWAP" | "FUTURES" | "OPTION";
  side: "buy" | "sell";
  order_type: string;
  size: string;
  size_unit: string;
  price?: string | null;
  leverage?: string | null;
  rationale: string;
  confidence?: number | null;
  mode: Mode;
  source: "llm" | "strategy" | "manual";
  metadata: Record<string, unknown>;
}

export interface RiskDecision {
  decision_id: string;
  intent_id: string;
  evaluated_at: string;
  approved: boolean;
  reasons: string[];
  violated_rules: string[];
  risk_config_hash: string;
  computed: Record<string, string>;
}

export interface LearningEvent {
  event_id: string;
  intent: TradeIntent;
  decision: RiskDecision;
  execution_result?: { ord_id: string; status: string } | null;
  outcome?: { realized_pnl_usd?: string | null } | null;
  logged_at: string;
}

export interface Balance {
  ccy: string;
  avail: string;
  total: string;
}

export interface Position {
  instId: string;
  posSide: string;
  pos: string;
  avgPx: string;
  upl: string;
  lever?: string | null;
}

export interface AccountState {
  as_of: string;
  mode: Mode;
  balances: Balance[];
  positions: Position[];
  open_orders_count: number;
  daily_realized_pnl_usd?: string | null;
}

export interface VerifyRow {
  check: string;
  status: "PASS" | "FAIL" | "NOT RUN" | "STALE";
  detail: string;
}

export interface StatusResponse {
  service: string;
  version: string;
  mode: Mode;
  allow_live: boolean;
}
