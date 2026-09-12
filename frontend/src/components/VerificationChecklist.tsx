import type { VerifyRow } from "../types";

const STATUS_LABEL: Record<VerifyRow["status"], string> = {
  PASS: "✅ PASS",
  FAIL: "❌ FAIL",
  "NOT RUN": "⏳ NOT RUN",
  STALE: "⚠️ STALE",
};

export function VerificationChecklist({ rows }: { rows: VerifyRow[] | null }) {
  if (!rows) {
    return <p>Loading verification checklist…</p>;
  }

  return (
    <table data-testid="verification-checklist">
      <thead>
        <tr>
          <th>Check</th>
          <th>Status</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.check}>
            <td>{row.check}</td>
            <td>{STATUS_LABEL[row.status] ?? row.status}</td>
            <td>{row.detail}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
