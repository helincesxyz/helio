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
