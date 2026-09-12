// Talks only to Helio's own local FastAPI service — never to OKX or the MCP
// server directly. See docs/ARCHITECTURE.md.
import type { AccountState, LearningEvent, StatusResponse, VerifyRow } from "../types";

const BASE_URL = "http://127.0.0.1:8787";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// 404 means "nothing logged yet" for these — a normal, expected state,
// not an error to surface to the user.
async function getOptionalJson<T>(path: string): Promise<T | null> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getStatus(): Promise<StatusResponse> {
  return getJson<StatusResponse>("/status");
}

export function getVerify(): Promise<VerifyRow[]> {
  return getJson<VerifyRow[]>("/verify");
}

export function getLearningHistory(limit = 50): Promise<LearningEvent[]> {
  return getJson<LearningEvent[]>(`/learning/history?limit=${limit}`);
}

export function getAccountState(): Promise<AccountState> {
  return getJson<AccountState>("/state/account");
}

export interface RiskConfig {
  allow_live: boolean;
  allowed_instrument_types: string[];
  allowed_instruments: string[];
  max_order_notional_usd: number;
  max_position_size_usd: number;
  max_open_positions: number;
  max_leverage: number;
  max_daily_loss_usd: number;
  exposure_cap_pct_of_equity: number;
}

export function getRiskConfig(): Promise<RiskConfig> {
  return getJson<RiskConfig>("/risk/config");
}

export interface EvidenceItem {
  name: string;
  passed: boolean;
  detail: string;
  hard_gate: boolean;
}

export interface TimeframeIndicators {
  timeframe: string;
  as_of: string;
  price: string;
  ema20: string;
  ema50: string;
  ema200: string;
  atr: string;
  atr_pct: string;
  volume_ratio: string;
  swing_high: string;
  swing_low: string;
  price_change_pct: string;
}

export interface ThesisRecord {
  decision_id: string;
  logged_at: string;
  thesis: {
    symbol: string;
    regime: string;
    strategy: string;
    strategy_version: string;
    action: "BUY" | "WAIT";
    confidence: number;
    thesis: string;
    evidence: string[];
    invalidation: { condition: string; price: string | null } | null;
    target: { price: string | null } | null;
  };
  prepared_state: {
    symbol: string;
    prepared_at: string;
    tf_4h: TimeframeIndicators;
    tf_1h: TimeframeIndicators;
    tf_15m: TimeframeIndicators;
    regime: string;
    regime_reason: string;
    evidence: EvidenceItem[];
    candidate_action: "BUY" | "WAIT";
  };
  validation: { valid: boolean; errors: string[]; warnings: string[] };
}

export function getThesisLatest(symbol = "BTC-USDT"): Promise<ThesisRecord | null> {
  return getOptionalJson<ThesisRecord>(`/thesis/latest?symbol=${symbol}`);
}

export function getThesisHistory(symbol = "BTC-USDT", limit = 20): Promise<ThesisRecord[]> {
  return getJson<ThesisRecord[]>(`/thesis/history?symbol=${symbol}&limit=${limit}`);
}

export interface GuardCheck {
  name: string;
  status: "PASS" | "FAIL";
  reason: string;
}

export interface GuardRecord {
  trade_intent_id: string;
  logged_at: string;
  trade_intent: {
    symbol: string;
    side: string;
    requested_notional: string;
    requested_quantity: string;
    thesis_id: string;
    confidence: number;
  };
  decision: {
    decision: "APPROVE" | "REJECT";
    checks: GuardCheck[];
    rejection_reasons: string[];
    policy_version: string;
  };
}

export function getGuardForThesis(thesisId: string): Promise<GuardRecord | null> {
  return getOptionalJson<GuardRecord>(`/guard/for-thesis/${thesisId}`);
}

export function getGuardLatest(symbol = "BTC-USDT"): Promise<GuardRecord | null> {
  return getOptionalJson<GuardRecord>(`/guard/latest?symbol=${symbol}`);
}

export interface Candle {
  ts: string;
  o: string;
  h: string;
  l: string;
  c: string;
  vol: string;
}

export interface MarketSnapshot {
  instId: string;
  as_of: string;
  last_price: string;
  candles: Candle[];
}

export function getMarketState(instId = "BTC-USDT"): Promise<MarketSnapshot | null> {
  return getOptionalJson<MarketSnapshot>(`/state/market?instId=${instId}`);
}
