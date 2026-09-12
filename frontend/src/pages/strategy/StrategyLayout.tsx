import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/strategy/overview", label: "Overview" },
  { to: "/strategy/performance", label: "Performance" },
  { to: "/strategy/decisions", label: "Decisions" },
  { to: "/strategy/trades", label: "Trades" },
  { to: "/strategy/memory", label: "Memory" },
];

export function StrategyLayout() {
  return (
    <div className="mx-auto max-w-5xl px-10 py-10">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-accent to-accent-strong" />
          <div>
            <h1 className="text-lg font-semibold text-ink">BTC Trend Breakout</h1>
            <p className="text-sm text-ink-muted">Trend-following BTC-USDT strategy</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted">v1</span>
          <button className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted transition-colors hover:text-ink">
            Settings
          </button>
          <button className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted transition-colors hover:text-ink">
            Share
          </button>
          <button
            disabled
            title="Execution is not implemented yet"
            className="cursor-not-allowed rounded-full bg-accent/30 px-4 py-1.5 text-xs font-medium text-white/60"
          >
            Automate
          </button>
        </div>
      </div>

      <nav className="mt-8 flex gap-6 border-b border-border">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `border-b-2 pb-3 text-sm transition-colors ${
                isActive ? "border-accent text-accent-strong" : "border-transparent text-ink-muted hover:text-ink"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <div className="pt-8">
        <Outlet />
      </div>
    </div>
  );
}
