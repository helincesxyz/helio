import { EmptyState } from "../../components/common/EmptyState";

export function Memory() {
  // learning/adjuster.py is an explicit stub (always returns None) and
  // strategy_version is always "v1" — there is no real strategy-evolution
  // history to show. Never fake a version-change timeline.
  return (
    <EmptyState
      title="Helio hasn't changed its strategy yet."
      description="Helio learns from real, completed trades — it hasn't finished enough of them yet to have anything to learn from. Once it does, changes will show up here as a timeline, with the evidence behind each one."
    />
  );
}
