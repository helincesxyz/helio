import { AreaSeries, LineSeries, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { MarketSnapshot } from "../../api/client";
import { computeEmaSeries } from "../../lib/ema";

function toUnixSeconds(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

export function PriceChart({ market }: { market: MarketSnapshot }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#8b8d98",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.09)" },
      timeScale: { borderColor: "rgba(255,255,255,0.09)" },
      crosshair: { mode: 0 },
      height: 360,
    });
    chartRef.current = chart;

    const closes = market.candles.map((c) => ({ time: toUnixSeconds(c.ts), close: parseFloat(c.c) }));

    const priceSeries = chart.addSeries(AreaSeries, {
      lineColor: "#3b82f6",
      lineWidth: 2,
      topColor: "rgba(59, 130, 246, 0.28)",
      bottomColor: "rgba(59, 130, 246, 0.0)",
      priceLineVisible: false,
      lastValueVisible: true,
    });
    priceSeries.setData(closes.map((c) => ({ time: c.time, value: c.close })));

    const emaConfigs: { period: number; color: string }[] = [
      { period: 20, color: "#6ea8ff" },
      { period: 50, color: "#9ca3af" },
      { period: 200, color: "#f0b429" },
    ];
    for (const { period, color } of emaConfigs) {
      const series = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      const emaClosesNumeric = market.candles.map((c) => ({
        time: toUnixSeconds(c.ts) as unknown as number,
        close: parseFloat(c.c),
      }));
      const points = computeEmaSeries(emaClosesNumeric, period);
      series.setData(points.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [market]);

  return (
    <div>
      <div ref={containerRef} data-testid="price-chart" />
      <div className="mt-3 flex gap-4 text-xs text-ink-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-3 bg-accent" /> Price
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-3" style={{ background: "#6ea8ff" }} /> EMA 20
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-3" style={{ background: "#9ca3af" }} /> EMA 50
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-3" style={{ background: "#f0b429" }} /> EMA 200
        </span>
      </div>
    </div>
  );
}
