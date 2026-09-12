import type { LearningEvent } from "../types";

export function TradeIntentFeed({ events }: { events: LearningEvent[] | null }) {
  if (!events) {
    return <p>Loading trade intent feed…</p>;
  }
  if (events.length === 0) {
    return <p data-testid="trade-intent-feed-empty">No trade intents logged yet.</p>;
  }

  return (
    <ul data-testid="trade-intent-feed">
      {events.map((event) => (
        <li key={event.event_id}>
          <strong>{event.intent.symbol}</strong> {event.intent.side} {event.intent.size}{" "}
          {event.intent.size_unit} via {event.intent.strategy_id} —{" "}
          {event.decision.approved ? "approved" : `rejected (${event.decision.violated_rules.join(", ")})`}
        </li>
      ))}
    </ul>
  );
}
