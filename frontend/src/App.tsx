import { getAccountState, getLearningHistory, getRiskConfig, getStatus, getVerify } from "./api/client";
import { AccountPanel } from "./components/AccountPanel";
import { RiskConfigView } from "./components/RiskConfigView";
import { StatusBanner } from "./components/StatusBanner";
import { TradeIntentFeed } from "./components/TradeIntentFeed";
import { VerificationChecklist } from "./components/VerificationChecklist";
import { usePolling } from "./hooks/usePolling";

export default function App() {
  const status = usePolling(getStatus, 5000);
  const verify = usePolling(getVerify, 5000);
  const history = usePolling(() => getLearningHistory(20), 5000);
  const account = usePolling(getAccountState, 5000);
  const riskConfig = usePolling(getRiskConfig, 15000);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto", padding: "1rem" }}>
      <h1>Helio</h1>
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
        <h2>Recent trade intents</h2>
        <TradeIntentFeed events={history.data} />
      </section>
    </main>
  );
}
