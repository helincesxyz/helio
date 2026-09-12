import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ThesisRecord } from "../src/api/client";
import { RiskSelector } from "../src/components/risk/RiskSelector";
import { buildRiskTierSummary } from "../src/lib/riskProfiles";
import { summarizePlainEnglish } from "../src/lib/summarize";

function makeRecord(overrides: {
  action: "BUY" | "WAIT";
  regime?: string;
  evidence?: { name: string; passed: boolean; hard_gate: boolean; detail: string }[];
}): ThesisRecord {
  return {
    decision_id: "d1",
    logged_at: new Date().toISOString(),
    thesis: {
      symbol: "BTC-USDT",
      regime: overrides.regime ?? "RANGE",
      strategy: "trend_breakout",
      strategy_version: "v1",
      action: overrides.action,
      confidence: 0.6,
      thesis: "technical prose",
      evidence: [],
      invalidation: null,
      target: null,
    },
    prepared_state: {
      symbol: "BTC-USDT",
      prepared_at: new Date().toISOString(),
      tf_4h: {} as never,
      tf_1h: {} as never,
      tf_15m: { timeframe: "15m", as_of: "", price: "50000", ema20: "", ema50: "", ema200: "", atr: "", atr_pct: "", volume_ratio: "", swing_high: "", swing_low: "", price_change_pct: "" },
      regime: overrides.regime ?? "RANGE",
      regime_reason: "",
      evidence: overrides.evidence ?? [],
      candidate_action: overrides.action,
    },
    validation: { valid: true, errors: [], warnings: [] },
  };
}

describe("summarizePlainEnglish", () => {
  it("gives an affirmative sentence for BUY", () => {
    const text = summarizePlainEnglish(makeRecord({ action: "BUY" }));
    expect(text).toMatch(/ready to act/i);
  });

  it("explains high volatility in plain English", () => {
    const text = summarizePlainEnglish(makeRecord({ action: "WAIT", regime: "HIGH_VOLATILITY_UNCLEAR" }));
    expect(text).toMatch(/too choppy/i);
  });

  it("explains insufficient volume in plain English (the spec's exact scenario)", () => {
    const text = summarizePlainEnglish(
      makeRecord({
        action: "WAIT",
        regime: "BULL_TREND",
        evidence: [
          { name: "trend_structure_bullish_4h", passed: true, hard_gate: true, detail: "" },
          { name: "breakout_volume_confirmed_1h", passed: false, hard_gate: true, detail: "" },
        ],
      }),
    );
    expect(text).toMatch(/hasn't confirmed the move strongly enough/i);
  });

  it("falls back to a generic honest sentence when nothing specific failed", () => {
    const text = summarizePlainEnglish(makeRecord({ action: "WAIT", regime: "BULL_TREND", evidence: [] }));
    expect(text).toMatch(/waiting for a clearer signal/i);
  });
});

describe("buildRiskTierSummary", () => {
  const config = {
    policy_version: "guard_v1",
    allowed_symbols: ["BTC-USDT"],
    allowed_instrument_types: ["SPOT"],
    max_leverage: 1,
    allowed_sides: ["buy"],
    max_simultaneous_positions: 1,
    max_notional_per_trade_usd: 100,
    max_daily_loss_usd: 50,
    max_portfolio_exposure_pct: 20,
    min_risk_reward: 1.5,
    min_confidence: 0.6,
  };

  it("balanced matches the real active config exactly", () => {
    const summary = buildRiskTierSummary(config, "balanced");
    expect(summary.maxTrade).toBe(100);
    expect(summary.isActivePolicy).toBe(true);
  });

  it("low and high are transparent scalings, not invented numbers", () => {
    expect(buildRiskTierSummary(config, "low").maxTrade).toBe(50);
    expect(buildRiskTierSummary(config, "high").maxTrade).toBe(150);
    expect(buildRiskTierSummary(config, "low").isActivePolicy).toBe(false);
  });
});

describe("RiskSelector", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          policy_version: "guard_v1",
          allowed_symbols: ["BTC-USDT"],
          allowed_instrument_types: ["SPOT"],
          max_leverage: 1,
          allowed_sides: ["buy"],
          max_simultaneous_positions: 1,
          max_notional_per_trade_usd: 100,
          max_daily_loss_usd: 50,
          max_portfolio_exposure_pct: 20,
          min_risk_reward: 1.5,
          min_confidence: 0.6,
        }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders real dollar figures from the fetched config, not hardcoded ones", async () => {
    render(<RiskSelector />);
    await waitFor(() => expect(screen.getByTestId("risk-selector")).toHaveTextContent("$50.00"));
    expect(screen.getByTestId("risk-selector")).toHaveTextContent("Max daily loss");
  });
});
