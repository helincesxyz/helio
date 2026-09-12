import type { ThesisRecord } from "../../api/client";
import { formatRelativeTime, titleCase } from "../../lib/format";
import { EvidenceList } from "../decision/EvidenceList";
import { ReasoningChecklist } from "./ReasoningChecklist";

export type ConversationTurnData =
  | { kind: "user"; id: string; text: string; timestamp: string }
  | { kind: "helio"; id: string; record: ThesisRecord; grounded: boolean };

const ACTION_STYLE: Record<string, string> = {
  BUY: "bg-positive/10 text-positive",
  WAIT: "bg-ink-muted/10 text-ink-muted",
};

export function ConversationTurn({ turn }: { turn: ConversationTurnData }) {
  if (turn.kind === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl rounded-2xl rounded-tr-sm border border-border bg-bg-glass px-4 py-3 text-sm text-ink">
          {turn.text}
        </div>
      </div>
    );
  }

  const { record, grounded } = turn;
  const { thesis, prepared_state } = record;

  return (
    <div className="max-w-2xl">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs text-accent-strong">
          H
        </span>
        <span className="text-sm font-medium text-ink">Helio</span>
        <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-ink-muted">
          {thesis.strategy_version}
        </span>
        <span className="text-xs text-ink-faint">
          {grounded ? "Based on the latest analysis" : "Automatic analysis"} · {formatRelativeTime(record.logged_at)}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-ink">{thesis.thesis}</p>

      <div className="mt-4">
        <ReasoningChecklist regime={thesis.regime} />
      </div>

      <div className="mt-4 flex items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${ACTION_STYLE[thesis.action]}`}>
          {thesis.action}
        </span>
        <span className="text-xs text-ink-muted">{titleCase(thesis.regime)}</span>
        <span className="text-xs text-ink-muted">Confidence {Math.round(thesis.confidence * 100)}%</span>
      </div>

      <div className="mt-4">
        <EvidenceList evidence={prepared_state.evidence} />
      </div>
    </div>
  );
}
