import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccountPanel } from "../src/components/AccountPanel";
import { RiskConfigView } from "../src/components/RiskConfigView";
import { StatusBanner } from "../src/components/StatusBanner";
import { TradeIntentFeed } from "../src/components/TradeIntentFeed";
import { VerificationChecklist } from "../src/components/VerificationChecklist";

describe("StatusBanner", () => {
  it("shows a connecting message when status is null", () => {
    render(<StatusBanner status={null} />);
    expect(screen.getByTestId("status-banner")).toHaveTextContent("Connecting");
  });

  it("shows mode and live-trading state", () => {
    render(<StatusBanner status={{ service: "helio", version: "0.1.0", mode: "simulation", allow_live: false }} />);
    expect(screen.getByTestId("status-banner")).toHaveTextContent("SIMULATION");
    expect(screen.getByTestId("status-banner")).toHaveTextContent("disabled");
  });
});

describe("VerificationChecklist", () => {
  it("renders every provided row", () => {
    render(
      <VerificationChecklist
        rows={[
          { check: "RISK ENGINE", status: "PASS", detail: "ok" },
          { check: "OKX CONNECTION", status: "NOT RUN", detail: "" },
        ]}
      />,
    );
    expect(screen.getByText("RISK ENGINE")).toBeInTheDocument();
    expect(screen.getByText("OKX CONNECTION")).toBeInTheDocument();
  });
});

describe("TradeIntentFeed", () => {
  it("shows an empty state with no events", () => {
    render(<TradeIntentFeed events={[]} />);
    expect(screen.getByTestId("trade-intent-feed-empty")).toBeInTheDocument();
  });
});

describe("AccountPanel", () => {
  it("shows an empty state with no account", () => {
    render(<AccountPanel account={null} />);
    expect(screen.getByTestId("account-panel-empty")).toBeInTheDocument();
  });
});

describe("RiskConfigView", () => {
  it("renders configured limits", () => {
    render(
      <RiskConfigView
        config={{
          allow_live: false,
          allowed_instrument_types: ["SPOT"],
          allowed_instruments: ["BTC-USDT"],
          max_order_notional_usd: 100,
          max_position_size_usd: 500,
          max_open_positions: 5,
          max_leverage: 3,
          max_daily_loss_usd: 50,
          exposure_cap_pct_of_equity: 20,
        }}
      />,
    );
    expect(screen.getByText("BTC-USDT")).toBeInTheDocument();
    expect(screen.getByText("no")).toBeInTheDocument();
  });
});
