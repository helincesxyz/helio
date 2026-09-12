import type { ThesisRecord } from "../api/client";

export function ThesisPanel({ record }: { record: ThesisRecord | null }) {
  if (!record) {
    return <p data-testid="thesis-panel-empty">No thesis logged yet — run GATE 2 (docs/runbooks/gate2_live_test.md).</p>;
  }

  const { thesis, prepared_state } = record;

  return (
    <div data-testid="thesis-panel">
      <dl>
        <dt>Regime</dt>
        <dd>{thesis.regime.replace(/_/g, " ")}</dd>
        <dt>Strategy</dt>
        <dd>
          {thesis.strategy.replace(/_/g, " ")} {thesis.strategy_version}
        </dd>
        <dt>Action</dt>
        <dd>
          <strong>{thesis.action}</strong>
        </dd>
        <dt>Confidence</dt>
        <dd>{thesis.confidence.toFixed(2)}</dd>
      </dl>

      <p>{thesis.thesis}</p>

      <h4>Evidence (deterministic)</h4>
      <ul>
        {prepared_state.evidence.map((item) => (
          <li key={item.name}>
            {item.passed ? "✓" : "✗"} {item.name.replace(/_/g, " ")} — {item.detail}
          </li>
        ))}
      </ul>

      {thesis.invalidation && (
        <p>
          <strong>Invalidation:</strong> {thesis.invalidation.condition}
          {thesis.invalidation.price ? ` (below $${thesis.invalidation.price})` : ""}
        </p>
      )}
      {thesis.target?.price && (
        <p>
          <strong>Target:</strong> ${thesis.target.price}
        </p>
      )}

      {!record.validation.valid && (
        <p role="alert">Thesis failed decision-quality validation: {record.validation.errors.join("; ")}</p>
      )}
    </div>
  );
}
