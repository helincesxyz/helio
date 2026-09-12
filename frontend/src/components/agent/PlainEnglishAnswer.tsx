import type { ThesisRecord } from "../../api/client";
import { summarizePlainEnglish } from "../../lib/summarize";
import { titleCase } from "../../lib/format";
import { EvidenceList } from "../decision/EvidenceList";
import { TechnicalDrawer } from "../decision/TechnicalDrawer";
import { ReasoningChecklist } from "./ReasoningChecklist";

export function PlainEnglishAnswer({ record }: { record: ThesisRecord }) {
  const { thesis, prepared_state } = record;

  return (
    <div>
      <p className="text-base leading-relaxed text-ink">{summarizePlainEnglish(record)}</p>

      <details className="group mt-4 rounded-2xl border border-border">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm text-ink-muted transition-colors hover:text-ink">
          See how Helio decided
        </summary>
        <div className="space-y-4 border-t border-border px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-bg-glass px-3 py-1 text-xs font-medium text-ink">{thesis.action}</span>
            <span className="text-xs text-ink-muted">{titleCase(prepared_state.regime)}</span>
            <span className="text-xs text-ink-muted">Confidence {Math.round(thesis.confidence * 100)}%</span>
          </div>
          <ReasoningChecklist regime={thesis.regime} />

          <details className="group rounded-xl border border-border">
            <summary className="cursor-pointer list-none px-3 py-2 text-xs text-ink-muted transition-colors hover:text-ink">
              Technical details
            </summary>
            <div className="space-y-4 border-t border-border px-3 py-3">
              <EvidenceList evidence={prepared_state.evidence} />
              <TechnicalDrawer data={record} />
            </div>
          </details>
        </div>
      </details>
    </div>
  );
}
