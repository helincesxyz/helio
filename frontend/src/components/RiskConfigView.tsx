import type { RiskConfig } from "../api/client";

export function RiskConfigView({ config }: { config: RiskConfig | null }) {
  if (!config) {
    return <p data-testid="risk-config-empty">Loading risk limits…</p>;
  }

  return (
    <dl data-testid="risk-config-view">
      <dt>Live trading allowed</dt>
      <dd>{config.allow_live ? "YES" : "no"}</dd>
      <dt>Allowed instruments</dt>
      <dd>{config.allowed_instruments.join(", ") || "(none configured)"}</dd>
      <dt>Max order notional</dt>
      <dd>${config.max_order_notional_usd}</dd>
      <dt>Max position size</dt>
      <dd>${config.max_position_size_usd}</dd>
      <dt>Max open positions</dt>
      <dd>{config.max_open_positions}</dd>
      <dt>Max leverage</dt>
      <dd>{config.max_leverage}x</dd>
      <dt>Max daily loss</dt>
      <dd>${config.max_daily_loss_usd}</dd>
      <dt>Exposure cap</dt>
      <dd>{config.exposure_cap_pct_of_equity}% of equity</dd>
    </dl>
  );
}
