import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AllocationComparison } from "../src/components/agent/AllocationComparison";
import { ApyComparison } from "../src/components/agent/ApyComparison";
import { explainWhy, isWhyFollowUp } from "../src/lib/summarize";
import { formatBtcQuantity } from "../src/lib/format";
import type { ThesisRecord } from "../src/api/client";

function makeRecord(overrides: {
  action: "BUY" | "WAIT";
  evidence?: { name: string; passed: boolean; hard_gate: boolean; detail: string }[];
}): ThesisRecord {
  return {
    decision_id: "d1",
    logged_at: new Date().toISOString(),
    thesis: {
      symbol: "BTC-USDT",
      regime: "BULL_TREND",
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
      tf_15m: {} as never,
      regime: "BULL_TREND",
      regime_reason: "clear uptrend on the 4H",
      evidence: overrides.evidence ?? [],
      candidate_action: overrides.action,
    },
    validation: { valid: true, errors: [], warnings: [] },
  };
}

describe("isWhyFollowUp", () => {
  it("matches bare why questions", () => {
    expect(isWhyFollowUp("why")).toBe(true);
    expect(isWhyFollowUp("Why?")).toBe(true);
    expect(isWhyFollowUp(" WHY ")).toBe(true);
  });

  it("does not match a longer question", () => {
    expect(isWhyFollowUp("why is bitcoin up today")).toBe(false);
  });
});

describe("explainWhy", () => {
  it("lists every hard-gate evidence check for a WAIT thesis", () => {
    const text = explainWhy(
      makeRecord({
        action: "WAIT",
        evidence: [
          { name: "trend_structure_bullish_4h", passed: true, hard_gate: true, detail: "4H trend is up" },
          { name: "breakout_volume_confirmed_1h", passed: false, hard_gate: true, detail: "volume too low" },
        ],
      }),
    );
    expect(text).toContain("4H trend is up");
    expect(text).toContain("volume too low");
    expect(text).toContain("1 of 2");
  });

  it("gives an affirmative summary for a BUY thesis", () => {
    const text = explainWhy(
      makeRecord({
        action: "BUY",
        evidence: [{ name: "trend_structure_bullish_4h", passed: true, hard_gate: true, detail: "4H trend is up" }],
      }),
    );
    expect(text).toMatch(/ready to act/i);
  });
});

describe("AllocationComparison", () => {
  it("renders only the fields actually present, no invented numbers", () => {
    render(<AllocationComparison comparison={{ cash: { amount: 500, ccy: "USDT" }, trade: { action: "WAIT", confidence: 0.4 } }} />);
    expect(screen.getByText(/Sitting in cash/i)).toBeInTheDocument();
    expect(screen.queryByText(/Real OKX Earn rate/i)).not.toBeInTheDocument();
  });
});

describe("formatBtcQuantity", () => {
  it("never renders scientific notation for tiny amounts", () => {
    expect(formatBtcQuantity("0.00008607")).toBe("0.00008607");
    expect(formatBtcQuantity(String(5 / 58091))).not.toMatch(/e-?\d/i);
  });

  it("trims trailing zeros", () => {
    expect(formatBtcQuantity("0.00100000")).toBe("0.001");
    expect(formatBtcQuantity("0.00000000")).toBe("0");
  });

  it("shows a dash for missing values", () => {
    expect(formatBtcQuantity(null)).toBe("—");
    expect(formatBtcQuantity(undefined)).toBe("—");
  });
});

describe("ApyComparison", () => {
  it("shows an honest empty state when there are no offers", () => {
    render(<ApyComparison comparison={{}} />);
    expect(screen.getByText(/No matching offers/i)).toBeInTheDocument();
  });

  it("renders real offers when present", () => {
    render(<ApyComparison comparison={{ offers: [{ product: "USDT Flexible", apy: 0.0289 }] }} />);
    expect(screen.getAllByText(/USDT Flexible/).length).toBeGreaterThan(0);
    expect(screen.getByText(/2\.9%/)).toBeInTheDocument();
  });
});
