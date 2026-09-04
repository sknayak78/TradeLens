import { useMemo } from "react";
import CandlestickChart from "@/components/charts/CandlestickChart";
import { expandCaseChart, type CaseChart } from "@/lib/howToUseLessons";

interface SituationChartProps {
  chart: CaseChart;
  testId?: string;
}

/**
 * Renders a case's deterministic situation chart using the shared candle chart.
 * The case data (candles + levels) is expanded here only; the chart component
 * owns all rendering/axes/EMA overlays.
 */
export function SituationChart({ chart, testId = "situation-chart" }: SituationChartProps) {
  const series = useMemo(() => expandCaseChart(chart.candles), [chart]);

  return (
    <div
      data-testid={testId}
      className="rounded-[4px] border border-[#D9DDE2] bg-white p-3"
    >
      <div
        data-testid="situation-chart-caption"
        className="mb-2 text-[10px] uppercase tracking-widest text-[#667085]"
      >
        The setup as it looked at the decision point
      </div>
      <CandlestickChart
        series={series}
        timeframe={chart.timeframe}
        support={chart.support ?? null}
        resistance={chart.resistance ?? null}
      />
    </div>
  );
}
