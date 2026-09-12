import { EmptyState } from "../../components/common/EmptyState";

export function Memory() {
  // learning/adjuster.py is an explicit stub (always returns None) and
  // strategy_version is always "v1" — there is no real strategy-evolution
  // history to show. Never fake a version-change timeline.
  return (
    <EmptyState
      title="Helio hasn't changed its strategy yet."
      description="Learning begins after verified trade outcomes. Once GATE 4 (execution) exists and produces real results, strategy revisions will appear here as a timeline — e.g. threshold changes, with the observed evidence behind each one."
    />
  );
}
