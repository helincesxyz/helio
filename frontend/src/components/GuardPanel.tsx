import type { GuardRecord } from "../api/client";

export function GuardPanel({ record }: { record: GuardRecord | null }) {
  if (!record) {
    return <p data-testid="guard-panel-empty">No risk evaluation logged yet for this thesis.</p>;
  }

  const { decision, trade_intent } = record;
  const approved = decision.decision === "APPROVE";

  return (
    <div data-testid="guard-panel">
      <p style={{ fontWeight: "bold", color: approved ? "green" : "crimson" }}>
        {approved ? "✓ APPROVED" : "✕ REJECTED"}
      </p>
      <p>
        {trade_intent.side.toUpperCase()} {trade_intent.symbol} — ${trade_intent.requested_notional} notional
        (policy {decision.policy_version})
      </p>

      {!approved && (
        <>
          <h4>Why</h4>
          <ul>
            {decision.rejection_reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </>
      )}

      <details>
        <summary>All risk checks ({decision.checks.length})</summary>
        <ul>
          {decision.checks.map((check) => (
            <li key={check.name}>
              {check.status === "PASS" ? "✓" : "✗"} {check.name.replace(/_/g, " ")} — {check.reason}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
