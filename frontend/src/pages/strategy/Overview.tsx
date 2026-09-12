import { ConfidenceGauge } from "../../components/decision/ConfidenceGauge";
import { EvidenceList } from "../../components/decision/EvidenceList";
import { PriceChart } from "../../components/chart/PriceChart";
import { EmptyState } from "../../components/common/EmptyState";
import { useHelioData } from "../../context/HelioDataContext";
import { formatRelativeTime, formatUsd, titleCase } from "../../lib/format";

function equity(balances: { ccy: string; total: string }[]): number {
  return balances
    .filter((b) => ["USD", "USDT", "USDC"].includes(b.ccy.toUpperCase()))
    .reduce((sum, b) => sum + parseFloat(b.total), 0);
}

function exposure(positions: { pos: string; avgPx: string }[]): number {
  return positions.reduce((sum, p) => sum + Math.abs(parseFloat(p.pos)) * parseFloat(p.avgPx), 0);
}

export function Overview() {
  const { thesisLatest, account, guardForLatest, market } = useHelioData();

  if (!thesisLatest) {
    return <EmptyState title="No analysis yet" description="Run a GATE 2 cycle to see Helio's current read on BTC-USDT." />;
  }

  const { thesis, prepared_state } = thesisLatest;
  const eq = account ? equity(account.balances) : null;
  const exp = account ? exposure(account.positions) : null;
  const riskChecks = guardForLatest?.decision.checks ?? null;
  const riskPassCount = riskChecks?.filter((c) => c.status === "PASS").length ?? null;

  return (
    <div className="flex flex-col gap-10">
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Action" value={thesis.action} accent={thesis.action === "BUY" ? "positive" : undefined} />
        <Stat label="Regime" value={titleCase(thesis.regime)} />
        <Stat label="BTC Price" value={`$${Number(prepared_state.tf_15m.price).toLocaleString()}`} />
        <Stat label="Account Equity" value={eq !== null ? formatUsd(eq) : "—"} />
        <Stat label="Exposure" value={exp !== null ? formatUsd(exp) : "—"} />
        <Stat
          label="Risk Status"
          value={
            guardForLatest
              ? `${riskPassCount}/${riskChecks!.length}`
              : thesis.action === "WAIT"
                ? "N/A"
                : "Pending"
          }
          accent={guardForLatest ? (guardForLatest.decision.decision === "APPROVE" ? "positive" : "negative") : undefined}
        />
      </div>

      <div className="flex items-center gap-8">
        <ConfidenceGauge confidence={thesis.confidence} />
        <p className="text-xs text-ink-faint">
          As of {formatRelativeTime(prepared_state.prepared_at)} · {prepared_state.regime_reason}
        </p>
      </div>

      {market ? (
        <PriceChart market={market} />
      ) : (
        <EmptyState title="No chart data yet" description="Waiting for real BTC-USDT candles to be posted to /state/market." />
      )}

      <div>
        <p className="mb-3 text-sm font-medium text-ink">Thesis</p>
        <p className="mb-5 max-w-2xl text-sm leading-relaxed text-ink-muted">{thesis.thesis}</p>
        <EvidenceList evidence={prepared_state.evidence} />
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: "positive" | "negative" }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-ink-muted decoration-dotted underline-offset-4">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold ${
          accent === "positive" ? "text-positive" : accent === "negative" ? "text-negative" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
