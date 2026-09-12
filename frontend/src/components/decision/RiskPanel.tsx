import type { GuardRecord } from "../../api/client";
import { titleCase } from "../../lib/format";

export function RiskPanel({ record, waitReason }: { record: GuardRecord | null; waitReason?: boolean }) {
  if (!record) {
    return (
      <div className="rounded-3xl border border-border p-6" data-testid="risk-panel-empty">
        <p className="text-sm font-medium text-ink">Risk engine</p>
        <p className="mt-1 text-sm text-ink-muted">
          {waitReason
            ? "No trade was proposed, so the deterministic risk layer was never engaged — a WAIT decision never reaches execution."
            : "No risk evaluation logged yet for this decision."}
        </p>
      </div>
    );
  }

  const { decision } = record;
  const approved = decision.decision === "APPROVE";
  const passCount = decision.checks.filter((c) => c.status === "PASS").length;

  return (
    <div className="rounded-3xl border border-border p-6" data-testid="risk-panel">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-ink">Risk engine</p>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            approved ? "bg-positive/10 text-positive" : "bg-negative/10 text-negative"
          }`}
        >
          {approved ? "APPROVED" : "REJECTED"}
        </span>
      </div>
      <p className="mt-1 text-2xl font-semibold text-ink">
        {passCount} / {decision.checks.length}
        <span className="ml-2 text-sm font-normal text-ink-muted">checks passed</span>
      </p>

      {!approved && decision.rejection_reasons.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {decision.rejection_reasons.map((reason, i) => (
            <li key={i} className="text-sm text-negative">
              • {reason}
            </li>
          ))}
        </ul>
      )}

      <details className="mt-4 group">
        <summary className="cursor-pointer text-xs text-ink-muted hover:text-ink">
          All checks ({decision.checks.length})
        </summary>
        <ul className="mt-3 space-y-1.5">
          {decision.checks.map((check) => (
            <li key={check.name} className="flex items-start gap-2 text-xs">
              <span className={check.status === "PASS" ? "text-positive" : "text-negative"}>
                {check.status === "PASS" ? "✓" : "✗"}
              </span>
              <span className="text-ink-muted">
                <span className="text-ink">{titleCase(check.name)}</span> — {check.reason}
              </span>
            </li>
          ))}
        </ul>
      </details>

      <p className="mt-5 border-t border-border pt-4 text-xs text-ink-faint">
        Helio can propose a trade. The deterministic risk layer decides whether it may execute.
      </p>
    </div>
  );
}
