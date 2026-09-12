import type { EvidenceItem } from "../../api/client";
import { titleCase } from "../../lib/format";

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  return (
    <ul className="flex flex-col gap-2.5" data-testid="evidence-list">
      {evidence.map((item) => (
        <li key={item.name} className="flex items-start gap-3 text-sm">
          <span className={item.passed ? "text-positive" : "text-ink-faint"}>
            {item.passed ? "✓" : "–"}
          </span>
          <div>
            <p className={item.passed ? "text-ink" : "text-ink-muted"}>{titleCase(item.name)}</p>
            <p className="text-xs text-ink-faint">{item.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
