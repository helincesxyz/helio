import { useEffect, useState } from "react";
import { getGuardProfiles, type GuardConfig, type RiskProfile } from "../../api/client";
import { buildRiskTierSummary, getStoredRiskTier, setStoredRiskTier, type RiskTier } from "../../lib/riskProfiles";
import { formatUsd } from "../../lib/format";

const TIERS: RiskTier[] = ["low", "balanced", "high"];

export function RiskSelector({ compact, onChange }: { compact?: boolean; onChange?: (tier: RiskTier) => void }) {
  const [profiles, setProfiles] = useState<Record<RiskProfile, GuardConfig> | null>(null);
  const [tier, setTier] = useState<RiskTier>(getStoredRiskTier());

  useEffect(() => {
    getGuardProfiles()
      .then(setProfiles)
      .catch(() => {});
  }, []);

  const select = (t: RiskTier) => {
    setTier(t);
    setStoredRiskTier(t);
    onChange?.(t);
  };

  return (
    <div data-testid="risk-selector">
      <div className="flex items-center justify-center gap-2">
        {TIERS.map((t) => (
          <button
            key={t}
            onClick={() => select(t)}
            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
              tier === t
                ? "border-accent bg-accent/10 text-accent-strong"
                : "border-border text-ink-muted hover:text-ink"
            }`}
          >
            {t === "low" ? "Low" : t === "balanced" ? "Balanced" : "High"}
          </button>
        ))}
      </div>

      {profiles && !compact && (
        <div className="mt-3 text-center">
          {(() => {
            const summary = buildRiskTierSummary(profiles[tier], tier);
            return (
              <>
                <p className="text-xs text-ink-muted">{summary.description}</p>
                <p className="mt-2 text-xs text-ink-faint">
                  Max trade {formatUsd(summary.maxTrade)} · Max daily loss {formatUsd(summary.maxDailyLoss)} · Max
                  positions {profiles[tier].max_simultaneous_positions}
                </p>
                <p className="mx-auto mt-1 max-w-md text-[11px] text-ink-faint">
                  This is the real limit Helio's risk engine enforces for every trade you send at this setting.
                </p>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}
