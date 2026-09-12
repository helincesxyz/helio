import { useNavigate } from "react-router-dom";
import { CommandBox } from "../components/agent/CommandBox";
import { SuggestedPrompts } from "../components/agent/SuggestedPrompts";
import { ConnectionBadge } from "../components/layout/ConnectionBadge";

export function Home() {
  const navigate = useNavigate();

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
        <p className="mt-4 text-lg text-ink-muted">Your autonomous trading agent.</p>

        <div className="mt-10 w-full">
          <CommandBox onSubmit={go} autoFocus />
          <SuggestedPrompts onSelect={go} />
        </div>
      </div>
    </div>
  );
}
