import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  getAccountState,
  getGuardForThesis,
  getMarketState,
  getStatus,
  getThesisHistory,
  getThesisLatest,
  getVerify,
  type GuardRecord,
  type MarketSnapshot,
  type ThesisRecord,
} from "../api/client";
import type { AccountState, StatusResponse, VerifyRow } from "../types";

const SYMBOL = "BTC-USDT";

interface HelioData {
  status: StatusResponse | null;
  statusError: string | null;
  verify: VerifyRow[] | null;
  connection: "connected" | "disconnected" | "unknown";
  account: AccountState | null;
  thesisLatest: ThesisRecord | null;
  thesisHistory: ThesisRecord[] | null;
  guardForLatest: GuardRecord | null;
  market: MarketSnapshot | null;
}

const HelioDataCtx = createContext<HelioData | null>(null);

function usePoll<T>(fetcher: () => Promise<T>, intervalMs: number, deps: unknown[] = []): T | null {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      fetcher()
        .then((result) => {
          if (!cancelled) setData(result);
        })
        .catch(() => {});
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return data;
}

export function HelioDataProvider({ children }: { children: ReactNode }) {
  const [statusError, setStatusError] = useState<string | null>(null);

  const status = usePoll(
    () =>
      getStatus()
        .then((s) => {
          setStatusError(null);
          return s;
        })
        .catch((err) => {
          setStatusError(err instanceof Error ? err.message : String(err));
          throw err;
        }),
    5000,
  );
  const verify = usePoll(getVerify, 8000);
  const account = usePoll(getAccountState, 5000);
  const thesisLatest = usePoll(() => getThesisLatest(SYMBOL), 5000);
  const thesisHistory = usePoll(() => getThesisHistory(SYMBOL, 20), 8000);
  const market = usePoll(() => getMarketState(SYMBOL), 15000);

  const decisionId = thesisLatest?.decision_id ?? null;
  const guardForLatest = usePoll(
    () => (decisionId ? getGuardForThesis(decisionId) : Promise.resolve(null)),
    5000,
    [decisionId],
  );

  const okxRow = verify?.find((r) => r.check === "OKX CONNECTION");
  const connection: HelioData["connection"] =
    okxRow?.status === "PASS" ? "connected" : okxRow?.status === "FAIL" ? "disconnected" : "unknown";

  const value: HelioData = {
    status,
    statusError,
    verify,
    connection,
    account,
    thesisLatest,
    thesisHistory,
    guardForLatest,
    market,
  };

  return <HelioDataCtx.Provider value={value}>{children}</HelioDataCtx.Provider>;
}

export function useHelioData(): HelioData {
  const ctx = useContext(HelioDataCtx);
  if (!ctx) throw new Error("useHelioData must be used within a HelioDataProvider");
  return ctx;
}
