import { EmptyState } from "../../components/common/EmptyState";

const METRIC_LABELS = [
  "Total Return",
  "Max Drawdown",
  "Sharpe Ratio",
  "Win Rate",
  "Profit Factor",
  "Average Win",
  "Average Loss",
  "Risk/Reward",
  "Trades",
];

export function Performance() {
  // GATE 4 (execution) does not exist yet, so there are no real trade
  // outcomes anywhere in the system to compute these metrics from. Never
  // fabricate — always show the honest empty state.
  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-3 gap-6 opacity-30 sm:grid-cols-5">
        {METRIC_LABELS.map((label) => (
          <div key={label}>
            <p className="text-xs uppercase tracking-wide text-ink-muted">{label}</p>
            <p className="mt-1 text-xl font-semibold text-ink">—</p>
          </div>
        ))}
      </div>
      <EmptyState
        title="No performance history yet"
        description="Helio hasn't executed any trades yet — live execution isn't wired up in this version. Performance metrics will appear here once real trade outcomes exist."
      />
    </div>
  );
}
