function qualitativeLabel(pct: number): string {
  if (pct >= 80) return "High";
  if (pct >= 60) return "Moderate";
  if (pct >= 40) return "Marginal";
  return "Low";
}

export function ConfidenceGauge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct / 100);

  return (
    <div className="flex items-center gap-4" data-testid="confidence-gauge">
      <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
        <circle cx="48" cy="48" r={radius} fill="none" stroke="var(--color-border)" strokeWidth="7" />
        <circle
          cx="48"
          cy="48"
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
        <text
          x="48"
          y="48"
          textAnchor="middle"
          dominantBaseline="middle"
          className="rotate-90 fill-ink text-2xl font-semibold"
          style={{ transformOrigin: "48px 48px" }}
        >
          {pct}
        </text>
      </svg>
      <div>
        <p className="text-xs uppercase tracking-wide text-ink-muted">Confidence</p>
        <p className="text-sm text-ink">{qualitativeLabel(pct)}</p>
      </div>
    </div>
  );
}
