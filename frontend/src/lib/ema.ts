// Client-side EMA computation, for chart visualization ONLY. Never used for
// any decision/evidence/risk display — those always render the backend's
// authoritative scalar values verbatim (see backend/src/helio/thesis/indicators.py,
// the canonical implementation this mirrors). Operates on real candle data
// fetched from Helio's own /state/market endpoint.
export interface EmaPoint {
  time: number; // unix seconds, for lightweight-charts
  value: number;
}

export function computeEmaSeries(
  closes: { time: number; close: number }[],
  period: number,
): EmaPoint[] {
  if (closes.length < period) return [];
  const k = 2 / (period + 1);
  const seed = closes.slice(0, period).reduce((sum, c) => sum + c.close, 0) / period;
  const points: EmaPoint[] = [{ time: closes[period - 1].time, value: seed }];
  let ema = seed;
  for (let i = period; i < closes.length; i++) {
    ema = closes[i].close * k + ema * (1 - k);
    points.push({ time: closes[i].time, value: ema });
  }
  return points;
}
