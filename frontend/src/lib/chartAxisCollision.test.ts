import {
  buildChartTimeAxisPlan,
  type ChartTimeAxisPlan,
  type ChartSeriesPoint,
  type ChartTimeAxisTick,
} from "@/lib/chartTimeAxis";
import { getXAxisLabelPresentation } from "@/lib/chartAxisFormat";
import {
  filterCollidingXAxisTicks,
  estimateRotatedLabelWidth,
  getXAxisEdgeMargins,
} from "@/lib/chartAxisCollision";

const IST_OFFSET = "+05:30";

function istTimestamp(
  year: number,
  month: number,
  day: number,
  hour = 10,
  minute = 0,
): string {
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  const h = String(hour).padStart(2, "0");
  const mi = String(minute).padStart(2, "0");
  return `${year}-${m}-${d}T${h}:${mi}:00${IST_OFFSET}`;
}

function buildIntradayWeekSeries(): ChartSeriesPoint[] {
  const series: ChartSeriesPoint[] = [];
  let value = 100;
  const days = [
    [17, 8],
    [18, 8],
    [19, 8],
    [20, 8],
    [21, 8],
    [24, 8],
    [25, 8],
    [26, 8],
    [27, 8],
    [28, 8],
  ] as const;
  days.forEach(([day, month]) => {
    for (let hour = 9; hour <= 15; hour += 1) {
      for (const minute of [0, 30]) {
        if (hour === 15 && minute === 30) continue;
        series.push({
          t: istTimestamp(2025, month, day, hour, minute),
          v: value,
        });
        value += 0.5;
      }
    }
  });
  return series;
}

function buildDailySeries(
  start: { year: number; month: number; day: number },
  tradingDays: number,
): ChartSeriesPoint[] {
  const series: ChartSeriesPoint[] = [];
  let cursor = new Date(Date.UTC(start.year, start.month - 1, start.day));
  let value = 100;
  while (series.length < tradingDays) {
    const weekday = cursor.getUTCDay();
    if (weekday !== 0 && weekday !== 6) {
      series.push({
        t: istTimestamp(
          cursor.getUTCFullYear(),
          cursor.getUTCMonth() + 1,
          cursor.getUTCDate(),
          10,
          0,
        ),
        v: value,
      });
      value += 1;
    }
    cursor = new Date(cursor.getTime() + 86_400_000);
  }
  return series;
}

function buildYearlySeries(): ChartSeriesPoint[] {
  return buildDailySeries({ year: 2025, month: 8, day: 21 }, 252);
}

/**
 * Real 1D data has a leading previous-session fragment (e.g. the final bars of
 * Aug 27) followed by the full final session (e.g. Aug 28 09:15–15:15). The
 * axis must start at 09:15 of the final session, never at the fragment.
 */
function buildFragmentThenFullSessionSeries(): ChartSeriesPoint[] {
  const series: ChartSeriesPoint[] = [];
  let value = 100;
  for (const [h, m] of [
    [14, 55],
    [15, 0],
    [15, 15],
  ] as const) {
    series.push({ t: istTimestamp(2025, 8, 27, h, m), v: value });
    value += 1;
  }
  for (let minute = 9 * 60 + 15; minute <= 15 * 60 + 15; minute += 15) {
    const hour = Math.floor(minute / 60);
    const mins = minute % 60;
    series.push({ t: istTimestamp(2025, 8, 28, hour, mins), v: value });
    value += 1;
  }
  return series;
}

/** Plot width derived the same way the chart does (width - margins - Y axis). */
function plotWidth(timeframe: string, chartWidth: number): number {
  const m = getXAxisEdgeMargins(timeframe as "1D" | "1W" | "1M" | "3M" | "1Y");
  return Math.max(1, chartWidth - m.left - m.right - 50);
}

function filterPlan(
  timeframe: "1D" | "1W" | "1M" | "3M" | "1Y",
  plan: ChartTimeAxisPlan,
  chartWidth: number,
): ChartTimeAxisTick[] {
  return filterCollidingXAxisTicks({
    timeframe,
    ticks: plan.ticks,
    useTimeScale: plan.useTimeScale,
    timeDomain: plan.timeDomain,
    seriesLength: plan.series.length,
    plotWidthPx: plotWidth(timeframe, chartWidth),
    presentation: getXAxisLabelPresentation(timeframe),
    series: plan.series,
  });
}

/** Confirm no two adjacent kept ticks horizontally overlap. */
function assertNoOverlap(
  timeframe: "1D" | "1W" | "1M" | "3M" | "1Y",
  plan: ChartTimeAxisPlan,
  kept: ChartTimeAxisTick[],
  chartWidth: number,
): void {
  const pw = plotWidth(timeframe, chartWidth);
  const ax = getXAxisLabelPresentation(timeframe);
  const position = (tick: ChartTimeAxisTick): number => {
    if (plan.useTimeScale && plan.timeDomain) {
      const span = plan.timeDomain[1] - plan.timeDomain[0];
      return ((tick.x - plan.timeDomain[0]) / span) * pw;
    }
    return (tick.index / Math.max(1, plan.series.length - 1)) * pw;
  };

  for (let i = 1; i < kept.length; i += 1) {
    const gap = position(kept[i]) - position(kept[i - 1]);
    const footprint = estimateRotatedLabelWidth(
      kept[i].label,
      10,
      ax.angle,
    );
    expect(gap).toBeGreaterThanOrEqual(footprint);
  }
}

describe("filterCollidingXAxisTicks (labelled)", () => {
  it("1D keeps no adjacent overlapping intraday labels", () => {
    const series: ChartSeriesPoint[] = [];
    for (let minute = 9 * 60 + 15; minute <= 15 * 60 + 30; minute += 15) {
      const hour = Math.floor(minute / 60);
      const mins = minute % 60;
      series.push({ t: istTimestamp(2026, 8, 21, hour, mins), v: 100 + minute });
    }
    const plan = buildChartTimeAxisPlan("1D", series, 720);
    const kept = filterPlan("1D", plan, 720);
    expect(kept.length).toBeGreaterThanOrEqual(2);
    expect(kept.length).toBeLessThanOrEqual(plan.series.length);
    assertNoOverlap("1D", plan, kept, 720);
  });

  it("1W does not render colliding 21 Aug and 24 Aug together when too close", () => {
    const series = buildIntradayWeekSeries();
    const plan = buildChartTimeAxisPlan("1W", series, 720);
    const kept = filterPlan("1W", plan, 720);
    assertNoOverlap("1W", plan, kept, 720);
  });

  it("3M stays readable and non-overlapping", () => {
    const series = buildDailySeries({ year: 2025, month: 6, day: 2 }, 66);
    const plan = buildChartTimeAxisPlan("3M", series, 720);
    const kept = filterPlan("3M", plan, 720);
    expect(kept.length).toBeGreaterThanOrEqual(2);
    assertNoOverlap("3M", plan, kept, 720);
  });

  it("1M stays readable and non-overlapping", () => {
    const series = buildDailySeries({ year: 2025, month: 7, day: 25 }, 22);
    const plan = buildChartTimeAxisPlan("1M", series, 720);
    const kept = filterPlan("1M", plan, 720);
    expect(kept.length).toBeGreaterThanOrEqual(2);
    assertNoOverlap("1M", plan, kept, 720);
  });

  it("1Y keeps month starts as the seed ticks and stays non-overlapping", () => {
    const series = buildYearlySeries();
    const plan = buildChartTimeAxisPlan("1Y", series, 900);
    const kept = filterPlan("1Y", plan, 900);
    expect(kept.length).toBeGreaterThanOrEqual(2);
    // Every kept label is still a month-start label (semantics preserved).
    kept.forEach((tick) => {
      expect(tick.label).toMatch(/\w{3} \d{4}/);
    });
    assertNoOverlap("1Y", plan, kept, 900);
  });

  it("preserves the first and last ticks", () => {
    const series = buildYearlySeries();
    const plan = buildChartTimeAxisPlan("1Y", series, 600);
    const kept = filterPlan("1Y", plan, 600);
    expect(kept[0].index).toBe(0);
    expect(kept[kept.length - 1].index).toBe(plan.series.length - 1);
  });

  it("does not re-introduce overlap even at narrow widths", () => {
    const scenarios: Array<
      ["1D" | "1W" | "1M" | "3M" | "1Y", ChartSeriesPoint[], number]
    > = [
      ["1D", buildIntradayWeekSeries().slice(0, 26), 420],
      ["1W", buildIntradayWeekSeries(), 420],
      ["1M", buildDailySeries({ year: 2025, month: 7, day: 25 }, 22), 420],
      ["3M", buildDailySeries({ year: 2025, month: 6, day: 2 }, 66), 420],
      ["1Y", buildYearlySeries(), 600],
    ];
    scenarios.forEach(([timeframe, series, width]) => {
      const plan = buildChartTimeAxisPlan(timeframe, series, width);
      const kept = filterPlan(timeframe, plan, width);
      assertNoOverlap(timeframe, plan, kept, width);
    });
  });
});

describe("estimateRotatedLabelWidth", () => {
  it("grows with label length", () => {
    const short = estimateRotatedLabelWidth("09", 10, 40);
    const long = estimateRotatedLabelWidth("14:30", 10, 40);
    expect(long).toBeGreaterThan(short);
  });

  it("equals text width when unrotated", () => {
    const flat = estimateRotatedLabelWidth("21 Aug", 10, 0);
    expect(flat).toBeCloseTo("21 Aug".length * 0.6 * 10, 1);
  });

  it("is never negative", () => {
    expect(estimateRotatedLabelWidth("", 10, 40)).toBe(0);
    expect(estimateRotatedLabelWidth("Aug 2025", 10, 40)).toBeGreaterThan(0);
  });
});

describe("getXAxisEdgeMargins", () => {
  it("returns positive breathing room for every timeframe", () => {
    for (const tf of ["1D", "1W", "1M", "3M", "1Y"]) {
      const m = getXAxisEdgeMargins(tf as "1D" | "1W" | "1M" | "3M" | "1Y");
      expect(m.left).toBeGreaterThan(0);
      expect(m.right).toBeGreaterThan(0);
    }
  });
});

describe("ER-0039 regression (tick distribution, selection is positional)", () => {
  const TFS = ["1D", "1W", "1M", "3M", "1Y"] as const;

  /** Pixel gap between two adjacent kept ticks under the plan's coordinate map. */
  function gapPx(
    timeframe: (typeof TFS)[number],
    plan: ChartTimeAxisPlan,
    a: ChartTimeAxisTick,
    b: ChartTimeAxisTick,
  ): number {
    const w = plan.useTimeScale && plan.timeDomain ? 900 : 720;
    const p = (t: ChartTimeAxisTick) => {
      if (plan.useTimeScale && plan.timeDomain && t.x) {
        const span = plan.timeDomain[1] - plan.timeDomain[0];
        return ((t.x - plan.timeDomain[0]) / span) * plotWidth(timeframe, w);
      }
      return (
        (t.index / Math.max(1, plan.series.length - 1)) * plotWidth(timeframe, w)
      );
    };
    return p(b) - p(a);
  }

  it("1D first tick is the session open (09:15), not the previous-session fragment", () => {
    const plan = buildChartTimeAxisPlan("1D", buildFragmentThenFullSessionSeries(), 720);
    const kept = filterPlan("1D", plan, 720);
    expect(kept[0].label).toBe("09:15");
    expect(kept[0].label).not.toBe("14:55");
  });

  it("1D ends at the final 15:15 of the session", () => {
    const plan = buildChartTimeAxisPlan("1D", buildFragmentThenFullSessionSeries(), 720);
    const kept = filterPlan("1D", plan, 720);
    expect(kept[kept.length - 1].label).toBe("15:15");
    assertNoOverlap("1D", plan, kept, 720);
  });

  it("1D labels are evenly distributed with no huge gap", () => {
    const plan = buildChartTimeAxisPlan("1D", buildIntradayWeekSeries(), 720);
    const kept = filterPlan("1D", plan, 720);
    const gaps = kept
      .slice(1)
      .map((_, i) => gapPx("1D", plan, kept[i], kept[i + 1]));
    const max = Math.max(...gaps);
    const min = Math.min(...gaps);
    // Even spacing: the largest gap is no more than ~2x the smallest.
    expect(max).toBeLessThanOrEqual(min * 2 + 1);
    assertNoOverlap("1D", plan, kept, 720);
  });

  it("1W drops the too-close 22/24 pair only when actually colliding", () => {
    const series = buildIntradayWeekSeries();
    const plan = buildChartTimeAxisPlan("1W", series, 720);
    const kept = filterPlan("1W", plan, 720);
    assertNoOverlap("1W", plan, kept, 720);
  });

  it("1W keeps a middle day (25 Aug) that the plan-thinned pool drops", () => {
    const series = buildIntradayWeekSeries();
    const plan = buildChartTimeAxisPlan("1W", series, 720);
    const planLabels = plan.ticks.map((t) => t.label);
    expect(planLabels).not.toContain("25 Aug");
    const kept = filterPlan("1W", plan, 720);
    const labels = kept.map((t) => t.label);
    expect(labels).toContain("25 Aug");
    assertNoOverlap("1W", plan, kept, 720);
  });

  it("1W keeps 29 Aug as the end-of-range tick when it is a valid day", () => {
    const days = [
      [21, 8],
      [24, 8],
      [25, 8],
      [26, 8],
      [27, 8],
      [28, 8],
      [29, 8],
    ] as const;
    const series: ChartSeriesPoint[] = [];
    let value = 100;
    days.forEach(([day, month]) => {
      for (let hour = 9; hour <= 15; hour += 1) {
        for (const minute of [0, 30]) {
          if (hour === 15 && minute === 30) continue;
          series.push({ t: istTimestamp(2025, month, day, hour, minute), v: value });
          value += 1;
        }
      }
    });
    const plan = buildChartTimeAxisPlan("1W", series, 720);
    const kept = filterPlan("1W", plan, 720);
    expect(kept[kept.length - 1].label).toBe("29 Aug");
    assertNoOverlap("1W", plan, kept, 720);
  });

  it("every timeframe stays non-overlapping across widths", () => {
    const cases: Array<(typeof TFS)[number]> = [...TFS];
    const seriesByTf: Record<(typeof TFS)[number], ChartSeriesPoint[]> = {
      "1D": buildIntradayWeekSeries(),
      "1W": buildIntradayWeekSeries(),
      "1M": buildDailySeries({ year: 2025, month: 7, day: 25 }, 22),
      "3M": buildDailySeries({ year: 2025, month: 6, day: 2 }, 66),
      "1Y": buildYearlySeries(),
    };
    for (const tf of cases) {
      for (const w of [420, 720, 1000]) {
        const plan = buildChartTimeAxisPlan(tf, seriesByTf[tf], w);
        const kept = filterPlan(tf, plan, w);
        assertNoOverlap(tf, plan, kept, w);
      }
    }
  });
});
