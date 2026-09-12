import { formatPct, formatUsd } from "../../lib/format";
import { TechnicalDrawer } from "../decision/TechnicalDrawer";

/**
 * Renders the `allocation_comparison` conversation-response kind. The
 * backend's `comparison` field is an untyped dict assembled live by Claude
 * Code from real MCP data (see docs/runbooks/conversation_fulfillment.md)
 * — this component renders whatever real fields are present and never
 * invents a number for one that's missing.
 */
export function AllocationComparison({ comparison }: { comparison: Record<string, unknown> }) {
  const cash = comparison.cash as { amount?: number; ccy?: string } | undefined;
  const earn = comparison.earn as { apy?: number; ccy?: string } | undefined;
  const trade = comparison.trade as { action?: string; confidence?: number } | undefined;

  return (
    <div className="space-y-4">
      <p className="text-base leading-relaxed text-ink">
        Here's how your idle cash compares to putting it to work right now.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cash?.amount !== undefined && (
          <div className="rounded-2xl border border-border bg-bg-glass p-4">
            <p className="text-xs uppercase tracking-wide text-ink-muted">Sitting in cash</p>
            <p className="mt-1 text-lg font-semibold text-ink">
              {formatUsd(cash.amount)} {cash.ccy ?? ""}
            </p>
          </div>
        )}
        {earn?.apy !== undefined && (
          <div className="rounded-2xl border border-border bg-bg-glass p-4">
            <p className="text-xs uppercase tracking-wide text-ink-muted">Real OKX Earn rate</p>
            <p className="mt-1 text-lg font-semibold text-ink">{formatPct(earn.apy * 100)} APY</p>
          </div>
        )}
        {trade?.action && (
          <div className="rounded-2xl border border-border bg-bg-glass p-4">
            <p className="text-xs uppercase tracking-wide text-ink-muted">BTC trade signal</p>
            <p className="mt-1 text-lg font-semibold text-ink">{trade.action}</p>
            {trade.confidence !== undefined && (
              <p className="text-xs text-ink-faint">{Math.round(trade.confidence * 100)}% confidence</p>
            )}
          </div>
        )}
      </div>
      <TechnicalDrawer data={comparison} />
    </div>
  );
}
