import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ConversationTimeline } from "../components/agent/ConversationTimeline";
import { CommandBox } from "../components/agent/CommandBox";
import type { ConversationTurnData } from "../components/agent/ConversationTurn";
import type { ThesisRecord } from "../api/client";
import { useHelioData } from "../context/HelioDataContext";

const EARN_NOT_CONNECTED_MESSAGE =
  "Helio can't act on idle-money yield yet — OKX Earn discovery isn't connected. This is on the roadmap, and Helio will never claim to have subscribed you to a yield product it hasn't actually executed.";
const BTC_ONLY_BANNER = "Helio only evaluates BTC-USDT today — full money optimization across cash, yield, and trading is on the roadmap.";

function buildHelioTurns(id: string, prompt: string, thesisLatest: ThesisRecord | null): ConversationTurnData[] {
  const lower = prompt.toLowerCase();

  if (lower.includes("earn")) {
    return [{ kind: "unavailable", id: `unavailable-${id}`, message: EARN_NOT_CONNECTED_MESSAGE }];
  }
  if (!thesisLatest) {
    return [{ kind: "unavailable", id: `unavailable-${id}`, message: "Helio hasn't run an analysis yet." }];
  }

  const needsBanner = !lower.includes("btc");
  return [
    {
      kind: "helio",
      id: `answer-${id}`,
      record: thesisLatest,
      grounded: true,
      banner: needsBanner ? BTC_ONLY_BANNER : undefined,
    },
  ];
}

export function Agent() {
  const { thesisLatest, thesisHistory } = useHelioData();
  const location = useLocation();
  const initialPrompt = (location.state as { prompt?: string } | null)?.prompt;

  // Turns added during this browser session (from the initial Home prompt,
  // or a follow-up typed here). Ephemeral by design — there is no live
  // inference backend, so every "answer" is the latest real GATE 2 record
  // (or an honest "not connected" message), never a freshly generated reply.
  const [sessionTurns, setSessionTurns] = useState<ConversationTurnData[]>([]);

  useEffect(() => {
    if (initialPrompt) {
      const id = `init-${Date.now()}`;
      setSessionTurns([
        { kind: "user", id: `user-${id}`, text: initialPrompt, timestamp: new Date().toISOString() },
        ...buildHelioTurns(id, initialPrompt, thesisLatest),
      ]);
    }
    // Only seed once, on arrival with a prompt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const historyTurns = useMemo<ConversationTurnData[]>(() => {
    const chronological = [...(thesisHistory ?? [])].reverse();
    return chronological
      .filter(
        (record) =>
          !sessionTurns.some((t) => t.kind === "helio" && t.record.decision_id === record.decision_id),
      )
      .map((record) => ({ kind: "helio" as const, id: record.decision_id, record, grounded: false }));
  }, [thesisHistory, sessionTurns]);

  const turns = [...historyTurns, ...sessionTurns];

  const onSubmit = (text: string) => {
    const id = `${Date.now()}`;
    setSessionTurns((prev) => [
      ...prev,
      { kind: "user", id: `user-${id}`, text, timestamp: new Date().toISOString() },
      ...buildHelioTurns(id, text, thesisLatest),
    ]);
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-8 text-lg font-medium text-ink">Agent</h1>
      <div className="flex-1 overflow-y-auto pb-6">
        <ConversationTimeline turns={turns} />
      </div>
      <div className="pt-4">
        <CommandBox onSubmit={onSubmit} placeholder="Ask a follow-up..." variant="consumer" />
      </div>
    </div>
  );
}
