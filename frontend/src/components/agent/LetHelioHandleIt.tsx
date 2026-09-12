import { useEffect, useState } from "react";
import { getGuardConfig, type GuardConfig } from "../../api/client";
import { formatUsd } from "../../lib/format";

export function LetHelioHandleIt({ onClose }: { onClose: () => void }) {
  const [config, setConfig] = useState<GuardConfig | null>(null);

  useEffect(() => {
    getGuardConfig()
      .then(setConfig)
      .catch(() => {});
  }, []);

  return (
    <div className="rounded-3xl border border-border bg-bg-glass p-6" data-testid="let-helio-handle-it">
      <div className="flex items-start justify-between">
        <p className="text-base font-medium text-ink">Let Helio manage this plan?</p>
        <button onClick={onClose} className="text-ink-muted hover:text-ink" aria-label="Close">
          ✕
        </button>
      </div>

      <p className="mt-3 text-sm text-ink-muted">Helio will:</p>
      <ul className="mt-2 space-y-1.5 text-sm text-ink-muted">
        <li>• Monitor BTC-USDT</li>
        <li>• Wait for entry conditions to be met</li>
        <li>• Apply your risk limits</li>
        <li>• Submit a trade only if the deterministic risk engine approves</li>
        <li>• Verify the resulting order</li>
      </ul>

      <div className="mt-5 border-t border-border pt-4">
        <p className="text-xs uppercase tracking-wide text-ink-muted">Maximum allocation</p>
        <p className="mt-1 text-xl font-semibold text-ink">
          {config ? formatUsd(config.max_notional_per_trade_usd) : "—"}
        </p>
      </div>

      <button
        disabled
        title="Live execution becomes available after execution setup"
        className="mt-5 w-full cursor-not-allowed rounded-full bg-accent/30 py-2.5 text-sm font-medium text-white/60"
      >
        Start monitoring
      </button>
      <p className="mt-2 text-center text-xs text-ink-faint">Live execution becomes available after execution setup.</p>
    </div>
  );
}
