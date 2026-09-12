import { useNavigate } from "react-router-dom";
import { CommandBox } from "../components/agent/CommandBox";
import { SuggestedPrompts } from "../components/agent/SuggestedPrompts";
import { ConnectionBadge } from "../components/layout/ConnectionBadge";
import { RiskSelector } from "../components/risk/RiskSelector";
import { useHelioData } from "../context/HelioDataContext";
import { formatUsd } from "../lib/format";

function equity(balances: { ccy: string; total: string }[]): number {
  return balances
    .filter((b) => ["USD", "USDT", "USDC"].includes(b.ccy.toUpperCase()))
    .reduce((sum, b) => sum + parseFloat(b.total), 0);
}

export function Home() {
  const navigate = useNavigate();
  const { account } = useHelioData();

  const go = (prompt: string) => {
    navigate("/agent", { state: { prompt } });
  };

  return (
    <div className="relative flex h-screen flex-col items-center justify-center overflow-hidden bg-bg px-6">
      {/* cinematic glow — CSS only, no external asset */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% 120%, rgba(59,130,246,0.20), transparent 60%), radial-gradient(ellipse 60% 40% at 20% 0%, rgba(59,130,246,0.08), transparent 60%)",
        }}
      />

      <div className="absolute left-6 top-6 text-sm font-semibold tracking-tight text-ink">Helio</div>
      <div className="absolute right-6 top-6">
        <ConnectionBadge />
      </div>

      <div className="relative z-10 flex w-full max-w-2xl flex-col items-center text-center">
        <h1 className="text-5xl font-semibold tracking-tight text-ink">Helio</h1>
        {account && (
          <p className="mt-3 text-sm text-ink-faint">{formatUsd(equity(account.balances))} available</p>
        )}
        <p className="mt-4 text-lg text-ink-muted">Tell Helio what you want your money to do.</p>

        <div className="mt-10 w-full">
          <CommandBox onSubmit={go} autoFocus variant="consumer" placeholder="I want to start investing..." />
          <SuggestedPrompts onSelect={go} />
        </div>

        <div className="mt-10 w-full">
          <RiskSelector />
        </div>
      </div>
    </div>
  );
}
