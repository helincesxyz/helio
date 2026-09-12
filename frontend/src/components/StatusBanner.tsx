import type { StatusResponse } from "../types";

export function StatusBanner({ status }: { status: StatusResponse | null }) {
  if (!status) {
    return (
      <div role="status" data-testid="status-banner" className="banner banner-unknown">
        Connecting to Helio service…
      </div>
    );
  }

  const modeClass = status.mode === "live" ? "banner-live" : "banner-simulation";
  return (
    <div role="status" data-testid="status-banner" className={`banner ${modeClass}`}>
      <strong>{status.mode.toUpperCase()}</strong> mode — Helio v{status.version} —{" "}
      live trading {status.allow_live ? "ENABLED" : "disabled"}
    </div>
  );
}
