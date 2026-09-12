import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommandBox } from "../src/components/agent/CommandBox";
import { EmptyState } from "../src/components/common/EmptyState";
import { ConfidenceGauge } from "../src/components/decision/ConfidenceGauge";
import { EvidenceList } from "../src/components/decision/EvidenceList";
import { RiskPanel } from "../src/components/decision/RiskPanel";

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(<EmptyState title="No live trades yet." description="Nothing has executed." />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("No live trades yet.");
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Nothing has executed.");
  });
});

describe("EvidenceList", () => {
  it("renders a passed and a failed item distinctly", () => {
    render(
      <EvidenceList
        evidence={[
          { name: "trend_structure_bullish_4h", passed: true, detail: "ok", hard_gate: true },
          { name: "breakout_volume_confirmed_1h", passed: false, detail: "0.1x", hard_gate: true },
        ]}
      />,
    );
    expect(screen.getByTestId("evidence-list")).toHaveTextContent("Trend Structure Bullish 4h");
    expect(screen.getByTestId("evidence-list")).toHaveTextContent("Breakout Volume Confirmed 1h");
  });
});

describe("RiskPanel", () => {
  it("shows the empty state when no record exists", () => {
    render(<RiskPanel record={null} />);
    expect(screen.getByTestId("risk-panel-empty")).toBeInTheDocument();
  });

  it("shows APPROVED and the check count for an approved decision", () => {
    render(
      <RiskPanel
        record={{
          trade_intent_id: "x",
          logged_at: new Date().toISOString(),
          trade_intent: {
            symbol: "BTC-USDT",
            side: "buy",
            requested_notional: "5",
            requested_quantity: "0.0001",
            thesis_id: "t1",
            confidence: 0.8,
          },
          decision: {
            decision: "APPROVE",
            checks: [
              { name: "allowed_symbol", status: "PASS", reason: "ok" },
              { name: "max_notional", status: "PASS", reason: "ok" },
            ],
            rejection_reasons: [],
            policy_version: "guard_v1",
          },
        }}
      />,
    );
    expect(screen.getByTestId("risk-panel")).toHaveTextContent("APPROVED");
    expect(screen.getByTestId("risk-panel")).toHaveTextContent("2 / 2");
  });
});

describe("ConfidenceGauge", () => {
  it("renders the rounded percentage", () => {
    render(<ConfidenceGauge confidence={0.62} />);
    expect(screen.getByTestId("confidence-gauge")).toHaveTextContent("62");
  });
});

describe("CommandBox", () => {
  it("calls onSubmit with the typed text and clears the input", () => {
    const onSubmit = vi.fn();
    render(<CommandBox onSubmit={onSubmit} />);
    const textarea = screen.getByPlaceholderText(/ask helio/i);
    fireEvent.change(textarea, { target: { value: "BTC breakout" } });
    fireEvent.submit(textarea.closest("form")!);
    expect(onSubmit).toHaveBeenCalledWith("BTC breakout");
  });

  it("does not submit empty input", () => {
    const onSubmit = vi.fn();
    render(<CommandBox onSubmit={onSubmit} />);
    const textarea = screen.getByPlaceholderText(/ask helio/i);
    fireEvent.submit(textarea.closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
