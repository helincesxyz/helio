import { useEffect, useState } from "react";
import { getGuardForThesis, type GuardRecord, type ThesisRecord } from "../../api/client";
import { DecisionPipeline, type PipelineStage } from "../../components/decision/DecisionPipeline";
import { EvidenceList } from "../../components/decision/EvidenceList";
import { RiskPanel } from "../../components/decision/RiskPanel";
import { TechnicalDrawer } from "../../components/decision/TechnicalDrawer";
import { EmptyState } from "../../components/common/EmptyState";
import { useHelioData } from "../../context/HelioDataContext";
import { formatRelativeTime, titleCase } from "../../lib/format";

const ACTION_STYLE: Record<string, string> = {
  BUY: "bg-positive/10 text-positive",
  WAIT: "bg-ink-muted/10 text-ink-muted",
};

function buildStages(record: ThesisRecord): PipelineStage[] {
  return [
    { label: "Observe", detail: "Market data read", status: "done" },
    { label: "Analyze", detail: titleCase(record.prepared_state.regime), status: "done" },
    { label: "Thesis", detail: record.thesis.action, status: "done" },
    { label: "Risk", detail: "Deterministic policy", status: "done" },
  ];
}

export function Decisions() {
  const { thesisHistory } = useHelioData();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [guardRecord, setGuardRecord] = useState<GuardRecord | null>(null);

  const selected = thesisHistory?.find((r) => r.decision_id === selectedId) ?? thesisHistory?.[0] ?? null;

  useEffect(() => {
    if (!selected) {
      setGuardRecord(null);
      return;
    }
    let cancelled = false;
    getGuardForThesis(selected.decision_id).then((r) => {
      if (!cancelled) setGuardRecord(r);
    });
    return () => {
      cancelled = true;
    };
  }, [selected?.decision_id]);

  if (!thesisHistory || thesisHistory.length === 0) {
    return <EmptyState title="No decisions logged yet" description="Run a GATE 2 cycle to produce Helio's first decision." />;
  }

  return (
    <div className="grid grid-cols-[280px_1fr] gap-8">
      <ul className="flex flex-col gap-1">
        {thesisHistory.map((record) => (
          <li key={record.decision_id}>
            <button
              onClick={() => setSelectedId(record.decision_id)}
              className={`w-full rounded-xl px-3 py-2.5 text-left transition-colors ${
                selected?.decision_id === record.decision_id ? "bg-bg-glass" : "hover:bg-bg-glass"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${ACTION_STYLE[record.thesis.action]}`}>
                  {record.thesis.action}
                </span>
                <span className="text-[11px] text-ink-faint">{formatRelativeTime(record.logged_at)}</span>
              </div>
              <p className="mt-1.5 text-xs text-ink-muted">{titleCase(record.thesis.regime)}</p>
            </button>
          </li>
        ))}
      </ul>

      {selected && (
        <div className="flex flex-col gap-8">
          <DecisionPipeline stages={buildStages(selected)} />

          <div>
            <div className="mb-3 flex items-center gap-3">
              <span className={`rounded-full px-3 py-1 text-xs font-medium ${ACTION_STYLE[selected.thesis.action]}`}>
                {selected.thesis.action}
              </span>
              <span className="text-sm text-ink-muted">Confidence {Math.round(selected.thesis.confidence * 100)}%</span>
            </div>
            <p className="max-w-2xl text-sm leading-relaxed text-ink-muted">{selected.thesis.thesis}</p>
          </div>

          <EvidenceList evidence={selected.prepared_state.evidence} />

          <RiskPanel record={guardRecord} waitReason={selected.thesis.action === "WAIT"} />

          <TechnicalDrawer data={selected} />
        </div>
      )}
    </div>
  );
}
