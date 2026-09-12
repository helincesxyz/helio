import { useHelioData } from "../../context/HelioDataContext";

const LABEL: Record<string, string> = {
  connected: "OKX connected",
  disconnected: "OKX disconnected",
  unknown: "OKX status unknown",
};
const LABEL_COMPACT: Record<string, string> = {
  connected: "Connected",
  disconnected: "Disconnected",
  unknown: "Unknown",
};

const DOT: Record<string, string> = {
  connected: "bg-positive shadow-[0_0_8px_#34d399]",
  disconnected: "bg-negative",
  unknown: "bg-ink-faint",
};

export function ConnectionBadge({ compact }: { compact?: boolean }) {
  const { connection, status } = useHelioData();
  const labels = compact ? LABEL_COMPACT : LABEL;

  return (
    <div
      className="flex w-fit max-w-full items-center gap-2 whitespace-nowrap rounded-full border border-border bg-bg-glass px-3 py-1.5 text-xs text-ink-muted backdrop-blur"
      title={compact ? `OKX ${connection}` : undefined}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[connection]}`} />
      <span className="truncate">{labels[connection]}</span>
      {status && !compact && (
        <>
          <span className="text-border-strong">·</span>
          <span className="uppercase tracking-wide">{status.mode}</span>
        </>
      )}
    </div>
  );
}
