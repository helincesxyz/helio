import type { ThesisRecord } from "../api/client";

/**
 * Deterministic, template-based plain-English restatement of a real
 * ThesisRecord. This is NOT an LLM call and does not invent anything — it
 * maps the record's real `action`/`regime`/`evidence` fields (already
 * produced by GATE 2) onto one of a fixed set of honest sentences. The full
 * technical prose (`thesis.thesis`) and structured evidence remain available
 * one level deeper via "See how Helio decided" / "Technical details".
 */
export function summarizePlainEnglish(record: ThesisRecord): string {
  const { thesis, prepared_state } = record;

  if (thesis.action === "BUY") {
    return "I found a setup I'm confident in. BTC's trend and momentum line up, so I'm ready to act within your risk limits.";
  }

  const failed = new Set(
    prepared_state.evidence.filter((e) => e.hard_gate && !e.passed).map((e) => e.name),
  );

  if (prepared_state.regime === "HIGH_VOLATILITY_UNCLEAR") {
    return "I'm waiting. The market is too choppy right now for a confident read, so I'd rather sit out than guess.";
  }
  if (failed.has("trend_structure_bullish_4h")) {
    return "I'm waiting. BTC's bigger-picture trend isn't clearly pointed up yet, so I don't see a reason to buy.";
  }
  if (failed.has("breakout_volume_confirmed_1h")) {
    return "I'm waiting. BTC hasn't confirmed the move strongly enough yet — buying now would mean taking risk without enough evidence.";
  }
  if (failed.has("breakout_level_broken_or_approached_1h")) {
    return "I'm waiting. Price hasn't broken through a key level yet, so there's no confirmed move to join.";
  }
  if (failed.has("entry_confirmation_not_chasing_15m")) {
    return "I'm waiting. Price has already run further than I'd want to chase — I'd rather wait for a better entry.";
  }
  return "I'm waiting for a clearer signal before putting your money to work.";
}
