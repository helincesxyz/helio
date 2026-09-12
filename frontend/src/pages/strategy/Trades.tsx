import { useEffect, useState } from "react";
import { getExecutions, type ExecutionLifecycle } from "../../api/client";
import { EmptyState } from "../../components/common/EmptyState";
import { formatBtcQuantity, formatRelativeTime } from "../../lib/format";

const COLUMNS = ["Date", "Type", "Trade ID", "Amount (BTC)", "Status", "Order ID", "Mode"];

const STATUS_LABELS: Record<string, string> = {
  FILLED: "Filled",
  PARTIALLY_FILLED: "Partially filled",
  SUBMITTED: "Submitted",
  LIVE: "Live",
  REJECTED: "Rejected",
  UNKNOWN: "Needs review",
};

export function Trades() {
  const [executions, setExecutions] = useState<ExecutionLifecycle[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    getExecutions()
      .then((rows) => {
        if (!cancelled) setExecutions(rows);
      })
      .catch(() => {
        if (!cancelled) setExecutions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-7 gap-4 border-b border-border pb-3 opacity-60">
        {COLUMNS.map((col) => (
          <p key={col} className="text-xs uppercase tracking-wide text-ink-muted">
            {col}
          </p>
        ))}
      </div>

      {executions === null ? (
        <p className="text-sm text-ink-muted">Loading...</p>
      ) : executions.length === 0 ? (
        <EmptyState
          title="No live trades yet."
          description="Nothing here is ever made up. Every attempt is checked against your risk limits first, and it's always labeled honestly as either a manual test run or something Helio did on its own — those aren't the same thing yet."
        />
      ) : (
        <div className="flex flex-col gap-2">
          {executions.map((exec) => (
            <div key={exec.execution_id} className="grid grid-cols-7 items-center gap-4 rounded-xl border border-border bg-bg-glass px-4 py-3 text-sm">
              <p className="text-ink-muted">{formatRelativeTime(exec.authorized_at)}</p>
              <p>
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs ${
                    exec.origin === "execution_test"
                      ? "border-border text-ink-muted"
                      : "border-accent text-accent-strong"
                  }`}
                >
                  {exec.origin === "execution_test" ? "Test run" : "Done automatically"}
                </span>
              </p>
              <p className="text-ink-faint">{exec.trade_intent_id.slice(0, 8)}</p>
              <p className="text-ink-muted">{formatBtcQuantity(exec.filled_quantity ?? exec.requested_quantity)}</p>
              <p className={exec.status === "FILLED" ? "text-positive" : exec.status === "REJECTED" ? "text-negative" : "text-ink-muted"}>
                {exec.status ? (STATUS_LABELS[exec.status] ?? exec.status) : "Waiting"}
              </p>
              <p className="text-ink-faint">{exec.okx_order_id ?? "—"}</p>
              <p className="text-ink-faint">{exec.mode ?? "—"}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
