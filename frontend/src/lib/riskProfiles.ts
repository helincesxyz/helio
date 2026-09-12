import type { GuardConfig } from "../api/client";

export type RiskTier = "low" | "balanced" | "high";

const STORAGE_KEY = "helio.riskTier";

export interface RiskTierSummary {
  tier: RiskTier;
  label: string;
  description: string;
  maxTrade: number;
  maxDailyLoss: number;
  maxExposurePct: number;
  minConfidence: number;
  minRiskReward: number;
}

const DESCRIPTIONS: Record<RiskTier, string> = {
  low: "Protect my money first.",
  balanced: "Look for growth without taking unnecessary risks.",
  high: "Accept larger swings for more opportunities.",
};

const LABELS: Record<RiskTier, string> = { low: "Low", balanced: "Balanced", high: "High" };

/**
 * Every number here comes straight from the real, backend-enforced
 * GuardConfig for this tier (fetched via GET /guard/profiles) — never
 * scaled or invented. Whichever tier is selected is the exact policy
 * POST /guard/evaluate applies for this request.
 */
export function buildRiskTierSummary(config: GuardConfig, tier: RiskTier): RiskTierSummary {
  return {
    tier,
    label: LABELS[tier],
    description: DESCRIPTIONS[tier],
    maxTrade: config.max_notional_per_trade_usd,
    maxDailyLoss: config.max_daily_loss_usd,
    maxExposurePct: config.max_portfolio_exposure_pct,
    minConfidence: config.min_confidence,
    minRiskReward: config.min_risk_reward,
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
