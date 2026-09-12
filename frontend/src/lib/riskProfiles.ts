import type { GuardConfig } from "../api/client";

export type RiskTier = "low" | "balanced" | "high";

const STORAGE_KEY = "helio.riskTier";

const SCALE: Record<RiskTier, number> = { low: 0.5, balanced: 1, high: 1.5 };

export interface RiskTierSummary {
  tier: RiskTier;
  label: string;
  description: string;
  maxTrade: number;
  maxDailyLoss: number;
  maxExposurePct: number;
  isActivePolicy: boolean;
  note: string;
}

const DESCRIPTIONS: Record<RiskTier, string> = {
  low: "Protect my money first.",
  balanced: "Look for growth without taking unnecessary risks.",
  high: "Accept larger swings for more opportunities.",
};

const LABELS: Record<RiskTier, string> = { low: "Low", balanced: "Balanced", high: "High" };

/**
 * Every dollar figure here is derived from Helio's one real, active GATE 3
 * config (fetched via GET /guard/config) — never invented. Low/High are a
 * transparent scaling of those real numbers for preview purposes; only
 * "balanced" (scale 1x) matches what the deterministic risk engine actually
 * enforces today. Selecting Low/High does not change backend enforcement —
 * see docs/ARCHITECTURE.md limitations.
 */
export function buildRiskTierSummary(config: GuardConfig, tier: RiskTier): RiskTierSummary {
  const scale = SCALE[tier];
  const isActivePolicy = tier === "balanced";
  return {
    tier,
    label: LABELS[tier],
    description: DESCRIPTIONS[tier],
    maxTrade: config.max_notional_per_trade_usd * scale,
    maxDailyLoss: config.max_daily_loss_usd * scale,
    maxExposurePct: Math.min(config.max_portfolio_exposure_pct * scale, 100),
    isActivePolicy,
    note: isActivePolicy
      ? "These are Helio's actual active limits."
      : `Preview only — ${scale}x Helio's active limits. Helio's deterministic risk engine still enforces the Balanced policy today; per-preference enforcement is planned.`,
  };
}

export function getStoredRiskTier(): RiskTier {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "low" || stored === "balanced" || stored === "high") return stored;
  } catch {
    // localStorage unavailable — fall through to default
  }
  return "balanced";
}

export function setStoredRiskTier(tier: RiskTier): void {
  try {
    localStorage.setItem(STORAGE_KEY, tier);
  } catch {
    // ignore — per-viewer convenience only
  }
}
