import { NavLink } from "react-router-dom";
import { ConnectionBadge } from "./ConnectionBadge";

const ITEMS = [
  { to: "/agent", label: "Agent" },
  { to: "/strategy/overview", label: "Strategy" },
  { to: "/strategy/performance", label: "Performance" },
  { to: "/strategy/trades", label: "Trades" },
  { to: "/strategy/memory", label: "Memory" },
];

export function NavRail() {
  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col justify-between border-r border-border px-4 py-6">
      <div>
        <NavLink to="/" className="mb-10 block px-2 text-lg font-semibold tracking-tight text-ink">
          Helio
        </NavLink>
        <nav className="flex flex-col gap-1">
          {ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-xl px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-bg-glass text-ink" : "text-ink-muted hover:text-ink"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="px-1">
        <ConnectionBadge compact />
      </div>
    </aside>
  );
}
