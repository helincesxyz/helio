import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { ConversationTimeline } from "../components/agent/ConversationTimeline";
import { CommandBox } from "../components/agent/CommandBox";
import type { ConversationTurnData } from "../components/agent/ConversationTurn";
import {
  getConversationRequest,
  getThesisHistory,
  postConversationRequest,
  type ThesisRecord,
} from "../api/client";
import { useHelioData } from "../context/HelioDataContext";
import { explainWhy, isWhyFollowUp } from "../lib/summarize";
import { getStoredRiskTier } from "../lib/riskProfiles";

const POLL_INTERVAL_MS = 1500;

async function findThesisRecord(thesisId: string, cached: ThesisRecord[]): Promise<ThesisRecord | null> {
  const hit = cached.find((r) => r.decision_id === thesisId);
  if (hit) return hit;
  try {
    const fresh = await getThesisHistory("BTC-USDT", 50);
    return fresh.find((r) => r.decision_id === thesisId) ?? null;
  } catch {
    return null;
  }
}

export function Agent() {
  const { thesisLatest, thesisHistory } = useHelioData();
  const location = useLocation();
  const initialPrompt = (location.state as { prompt?: string } | null)?.prompt;

  // Turns added during this browser session. Ephemeral by design: each
  // "thesis" answer is fulfilled live via the conversation bridge (Claude
  // Code fetching genuinely fresh OKX data), never fabricated client-side.
  const [sessionTurns, setSessionTurns] = useState<ConversationTurnData[]>([]);
  const [pendingRequestId, setPendingRequestId] = useState<string | null>(null);
  const lastRecordRef = useRef<ThesisRecord | null>(thesisLatest);
  const seededRef = useRef(false);
  const pollTargets = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    if (thesisLatest) lastRecordRef.current = thesisLatest;
  }, [thesisLatest]);

  const resolvePendingTurn = (pendingId: string, resolved: ConversationTurnData) => {
    setSessionTurns((prev) => prev.map((t) => (t.id === pendingId ? resolved : t)));
  };

  const submit = async (text: string) => {
    const id = `${Date.now()}`;

    if (isWhyFollowUp(text) && lastRecordRef.current) {
      setSessionTurns((prev) => [
        ...prev,
        { kind: "user", id: `user-${id}`, text, timestamp: new Date().toISOString() },
        { kind: "why", id: `why-${id}`, text: explainWhy(lastRecordRef.current!), timestamp: new Date().toISOString() },
      ]);
      return;
    }

    const pendingId = `pending-${id}`;
    setSessionTurns((prev) => [
      ...prev,
      { kind: "user", id: `user-${id}`, text, timestamp: new Date().toISOString() },
      { kind: "pending", id: pendingId },
    ]);

    try {
      const request = await postConversationRequest(text, getStoredRiskTier());
      setPendingRequestId(request.request_id);
      // Stash which session turn to replace once this request resolves.
      pollTargets.current.set(request.request_id, pendingId);
    } catch {
      resolvePendingTurn(pendingId, {
        kind: "error",
        id: pendingId,
        message: "Couldn't reach Helio's backend to submit that request.",
      });
    }
  };

  useEffect(() => {
    if (!pendingRequestId) return;
    const interval = setInterval(async () => {
      try {
        const record = await getConversationRequest(pendingRequestId);
        if (record.status === "PENDING") return;

        const pendingId = pollTargets.current.get(pendingRequestId) ?? pendingRequestId;
        pollTargets.current.delete(pendingRequestId);
        setPendingRequestId(null);

        const response = record.response;
        if (record.status === "FAILED" || !response || response.kind === "error") {
          resolvePendingTurn(pendingId, {
            kind: "error",
            id: pendingId,
            message: response?.message ?? "Helio couldn't complete that request.",
          });
          return;
        }

        if (response.kind === "unavailable") {
          resolvePendingTurn(pendingId, { kind: "unavailable", id: pendingId, message: response.message ?? "Not available yet." });
          return;
        }

        if (response.kind === "thesis" && response.thesis_id) {
          const thesisRecord = await findThesisRecord(response.thesis_id, thesisHistory ?? []);
          if (!thesisRecord) {
            resolvePendingTurn(pendingId, {
              kind: "error",
              id: pendingId,
              message: "Helio answered, but the underlying analysis couldn't be loaded.",
            });
            return;
          }
          lastRecordRef.current = thesisRecord;
          resolvePendingTurn(pendingId, { kind: "helio", id: pendingId, record: thesisRecord, grounded: true });
          return;
        }

        if (response.kind === "allocation_comparison" && response.comparison) {
          resolvePendingTurn(pendingId, {
            kind: "allocation_comparison",
            id: pendingId,
            comparison: response.comparison,
            timestamp: response.answered_at,
          });
          return;
        }

        if (response.kind === "apy_comparison" && response.comparison) {
          resolvePendingTurn(pendingId, {
            kind: "apy_comparison",
            id: pendingId,
            comparison: response.comparison,
            timestamp: response.answered_at,
          });
          return;
        }

        resolvePendingTurn(pendingId, { kind: "error", id: pendingId, message: "Helio returned an unrecognized response." });
      } catch {
        // Transient fetch failure — keep polling until the interval clears.
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingRequestId]);

  useEffect(() => {
    if (initialPrompt && !seededRef.current) {
      seededRef.current = true;
      submit(initialPrompt);
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

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-8 py-10">
      <h1 className="mb-8 text-lg font-medium text-ink">Agent</h1>
      <div className="flex-1 overflow-y-auto pb-6">
        <ConversationTimeline turns={turns} />
      </div>
      <div className="pt-4">
        <CommandBox onSubmit={submit} placeholder="Ask a follow-up..." variant="consumer" />
      </div>
    </div>
  );
}
