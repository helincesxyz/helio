import { ConversationTurn, type ConversationTurnData } from "./ConversationTurn";

export function ConversationTimeline({ turns }: { turns: ConversationTurnData[] }) {
  if (turns.length === 0) {
    return <p className="text-sm text-ink-muted">No analysis has run yet.</p>;
  }

  return (
    <div className="flex flex-col gap-8" data-testid="conversation-timeline">
      {turns.map((turn) => (
        <ConversationTurn key={turn.id} turn={turn} />
      ))}
    </div>
  );
}
