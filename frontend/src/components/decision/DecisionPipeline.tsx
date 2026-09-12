export type PipelineStageStatus = "done" | "active" | "pending";

export interface PipelineStage {
  label: string;
  detail: string;
  status: PipelineStageStatus;
}

const DOT: Record<PipelineStageStatus, string> = {
  done: "bg-accent border-accent",
  active: "bg-accent/20 border-accent animate-pulse",
  pending: "bg-transparent border-border-strong",
};

export function DecisionPipeline({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex items-start" data-testid="decision-pipeline">
      {stages.map((stage, i) => (
        <div key={stage.label} className="flex flex-1 flex-col items-start">
          <div className="flex w-full items-center">
            <span className={`h-3 w-3 shrink-0 rounded-full border-2 ${DOT[stage.status]}`} />
            {i < stages.length - 1 && (
              <span
                className={`mx-1 h-px flex-1 ${stage.status === "done" ? "bg-accent" : "bg-border"}`}
              />
            )}
          </div>
          <p
            className={`mt-2 text-xs font-medium uppercase tracking-wide ${
              stage.status === "pending" ? "text-ink-faint" : "text-ink"
            }`}
          >
            {stage.label}
          </p>
          <p className="mt-0.5 text-xs text-ink-muted">{stage.detail}</p>
        </div>
      ))}
    </div>
  );
}
