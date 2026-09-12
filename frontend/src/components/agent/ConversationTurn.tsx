import type { ThesisRecord } from "../../api/client";
import { formatRelativeTime } from "../../lib/format";
import { PlainEnglishAnswer } from "./PlainEnglishAnswer";

export type ConversationTurnData =
  | { kind: "user"; id: string; text: string; timestamp: string }
  | { kind: "helio"; id: string; record: ThesisRecord; grounded: boolean; banner?: string }
  | { kind: "unavailable"; id: string; message: string };

function HelioIdentity({ caption }: { caption: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs text-accent-strong">
        H
      </span>
      <span className="text-sm font-medium text-ink">Helio</span>
      <span className="text-xs text-ink-faint">{caption}</span>
    </div>
  );
}

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

  if (turn.kind === "unavailable") {
    return (
      <div className="max-w-2xl">
        <HelioIdentity caption="Not connected yet" />
        <p className="text-base leading-relaxed text-ink">{turn.message}</p>
      </div>
    );
  }

  const { record, grounded, banner } = turn;
  const { thesis } = record;

  return (
    <div className="max-w-2xl">
      <HelioIdentity
        caption={`${grounded ? "Based on the latest analysis" : "Automatic analysis"} · ${formatRelativeTime(record.logged_at)}`}
      />

      {banner && (
        <div className="mb-3 rounded-xl border border-border bg-bg-glass px-3 py-2 text-xs text-ink-muted">
          {banner}
        </div>
      )}

      <PlainEnglishAnswer record={record} />

      <p className="mt-3 text-xs text-ink-faint">Strategy: {thesis.strategy_version}</p>
    </div>
  );
}
