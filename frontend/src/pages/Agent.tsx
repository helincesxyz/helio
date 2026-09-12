import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ConversationTimeline } from "../components/agent/ConversationTimeline";
import { CommandBox } from "../components/agent/CommandBox";
import type { ConversationTurnData } from "../components/agent/ConversationTurn";
import { useHelioData } from "../context/HelioDataContext";

export function Agent() {
  const { thesisLatest, thesisHistory } = useHelioData();
  const location = useLocation();
  const initialPrompt = (location.state as { prompt?: string } | null)?.prompt;

  // Turns added during this browser session (from the initial Home prompt,
  // or a follow-up typed here). Ephemeral by design — there is no live
  // inference backend, so every "answer" is the latest real GATE 2 record,
  // honestly labeled as such, not a freshly generated reply.
  const [sessionTurns, setSessionTurns] = useState<ConversationTurnData[]>([]);

  useEffect(() => {
    if (initialPrompt && thesisLatest) {
      setSessionTurns([
        { kind: "user", id: `user-init-${Date.now()}`, text: initialPrompt, timestamp: new Date().toISOString() },
        { kind: "helio", id: `answer-init-${Date.now()}`, record: thesisLatest, grounded: true },
      ]);
    }
    // Only seed once, on arrival with a prompt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const historyTurns = useMemo<ConversationTurnData[]>(() => {
    const chronological = [...(thesisHistory ?? [])].reverse();
    return chronological
      .filter((record) => !sessionTurns.some((t) => t.kind === "helio" && t.record.decision_id === record.decision_id))
      .map((record) => ({ kind: "helio" as const, id: record.decision_id, record, grounded: false }));
  }, [thesisHistory, sessionTurns]);

  const turns = [...historyTurns, ...sessionTurns];

  const onSubmit = (text: string) => {
    if (!thesisLatest) return;
    setSessionTurns((prev) => [
      ...prev,
      { kind: "user", id: `user-${Date.now()}`, text, timestamp: new Date().toISOString() },
      { kind: "helio", id: `answer-${Date.now()}`, record: thesisLatest, grounded: true },
    ]);
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-8 text-lg font-medium text-ink">Agent</h1>
      <div className="flex-1 overflow-y-auto pb-6">
        <ConversationTimeline turns={turns} />
      </div>
      <div className="pt-4">
        <CommandBox onSubmit={onSubmit} placeholder="Ask a follow-up..." />
      </div>
    </div>
  );
}
