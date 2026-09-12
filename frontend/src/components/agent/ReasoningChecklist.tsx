import { titleCase } from "../../lib/format";

export function ReasoningChecklist({ regime }: { regime: string }) {
  const rows = [
    { label: "Reading market", detail: `4H regime — ${titleCase(regime)}` },
    { label: "Evaluating setup", detail: "1H structure" },
    { label: "Confirming entry", detail: "15m data" },
    { label: "Checking risk", detail: "deterministic policy" },
  ];

  return (
    <div className="rounded-2xl border border-border bg-bg-glass p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-ink-muted">Reasoning</p>
      <ul className="space-y-2">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center gap-2 text-sm">
            <span className="text-positive">✓</span>
            <span className="text-ink">{row.label}</span>
            <span className="text-ink-faint">— {row.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
