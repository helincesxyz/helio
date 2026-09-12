import { useEffect, useState } from "react";
import {
  getAccountState,
  getGuardForThesis,
  getLearningHistory,
  getRiskConfig,
  getStatus,
  getThesisLatest,
  getVerify,
  type GuardRecord,
} from "../api/client";
import { AccountPanel } from "../components/AccountPanel";
import { GuardPanel } from "../components/GuardPanel";
import { RiskConfigView } from "../components/RiskConfigView";
import { StatusBanner } from "../components/StatusBanner";
import { ThesisPanel } from "../components/ThesisPanel";
import { TradeIntentFeed } from "../components/TradeIntentFeed";
import { VerificationChecklist } from "../components/VerificationChecklist";
import { usePolling } from "../hooks/usePolling";

export function Debug() {
  const status = usePolling(getStatus, 5000);
  const verify = usePolling(getVerify, 5000);
  const history = usePolling(() => getLearningHistory(20), 5000);
  const account = usePolling(getAccountState, 5000);
  const riskConfig = usePolling(getRiskConfig, 15000);
  const thesis = usePolling(() => getThesisLatest("BTC-USDT"), 5000);

  const [guardRecord, setGuardRecord] = useState<GuardRecord | null>(null);
  const decisionId = thesis.data?.decision_id ?? null;
  useEffect(() => {
    if (!decisionId) {
      setGuardRecord(null);
      return;
    }
    let cancelled = false;
    const tick = () => {
      getGuardForThesis(decisionId)
        .then((record) => {
          if (!cancelled) setGuardRecord(record);
        })
        .catch(() => {});
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [decisionId]);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto", padding: "1rem" }}>
      <h1>Helio — Developer</h1>
      <p style={{ color: "#888", fontSize: 13 }}>
        Raw backend health and state. The primary product UI lives at <code>/</code>.
      </p>
      <StatusBanner status={status.data} />
      {status.error && <p role="alert">Could not reach Helio service: {status.error}</p>}

      <section>
        <h2>Verification checklist</h2>
        <VerificationChecklist rows={verify.data} />
      </section>

      <section>
        <h2>Account (read-only)</h2>
        <AccountPanel account={account.data ?? null} />
      </section>

      <section>
        <h2>Active risk limits</h2>
        <RiskConfigView config={riskConfig.data} />
      </section>

      <section>
        <h2>Latest thesis (GATE 2)</h2>
        <ThesisPanel record={thesis.data ?? null} />
      </section>

      <section>
        <h2>Risk check (GATE 3)</h2>
        <GuardPanel record={guardRecord} />
      </section>

      <section>
        <h2>Recent trade intents</h2>
        <TradeIntentFeed events={history.data} />
      </section>
    </main>
  );
}
