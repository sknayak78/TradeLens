import {
  buildChartTimeAxisPlan,
  estimateTickLabelOverlap,
  selectChartXAxisTickIndices,
  type ChartSeriesPoint,
} from "@/lib/chartTimeAxis";

const IST_OFFSET = "+05:30";

function istTimestamp(
  year: number,
  month: number,
  day: number,
  hour = 10,
  minute = 0,
): string {
  const monthText = String(month).padStart(2, "0");
  const dayText = String(day).padStart(2, "0");
  const hourText = String(hour).padStart(2, "0");
  const minuteText = String(minute).padStart(2, "0");
  return `${year}-${monthText}-${dayText}T${hourText}:${minuteText}:00${IST_OFFSET}`;
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

function labelsFor(
  timeframe: "1D" | "1W" | "1M" | "3M" | "1Y",
  series: ChartSeriesPoint[],
  chartWidthPx = 720,
): string[] {
  return buildChartTimeAxisPlan(timeframe, series, chartWidthPx).ticks.map(
    (tick) => tick.label,
  );
}

describe("chartTimeAxis", () => {
  it("1D generates readable intraday ticks", () => {
    const series: ChartSeriesPoint[] = [];
    for (let minute = 9 * 60 + 15; minute <= 15 * 60 + 30; minute += 15) {
      const hour = Math.floor(minute / 60);
      const mins = minute % 60;
      series.push({
        t: istTimestamp(2026, 8, 21, hour, mins),
        v: 100 + minute,
      });
    }

    const plan = buildChartTimeAxisPlan("1D", series, 720);
    expect(plan.ticks.length).toBeGreaterThanOrEqual(4);
    expect(plan.ticks.length).toBeLessThanOrEqual(8);
    plan.ticks.forEach((tick) => {
      expect(tick.label).toMatch(/^\d{2}:\d{2}$/);
    });
    expect(plan.tickValues[0]).toBe(series[0].t);
    expect(plan.tickValues[plan.tickValues.length - 1]).toBe(
      series[series.length - 1].t,
    );
  });

  it("1W generates daily ticks rather than every intraday datapoint", () => {
    const series = buildIntradayWeekSeries();
    expect(series.length).toBeGreaterThan(20);

    const plan = buildChartTimeAxisPlan("1W", series, 720);
    expect(plan.ticks.length).toBeLessThanOrEqual(7);
    expect(plan.ticks.length).toBeGreaterThanOrEqual(4);

    const uniqueLabels = new Set(plan.ticks.map((tick) => tick.label));
    expect(uniqueLabels.size).toBe(plan.ticks.length);
    plan.ticks.forEach((tick) => {
      expect(tick.label).toMatch(/^\d{2} \w{3}$/);
    });
  });

  it("1M generates sensible date intervals", () => {
    const series = buildDailySeries({ year: 2025, month: 7, day: 25 }, 22);
    const labels = labelsFor("1M", series, 720);

    expect(labels.length).toBeGreaterThanOrEqual(4);
    expect(labels.length).toBeLessThanOrEqual(7);
    expect(new Set(labels).size).toBe(labels.length);
    expect(labels[0]).toMatch(/Jul|Aug/);
    expect(labels[labels.length - 1]).toMatch(/Aug/);
  });

  it("3M generates sensible weekly/date intervals", () => {
    const series = buildDailySeries({ year: 2025, month: 6, day: 2 }, 66);
    const labels = labelsFor("3M", series, 720);

    expect(labels.length).toBeGreaterThanOrEqual(6);
    expect(labels.length).toBeLessThanOrEqual(10);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("1Y generates monthly ticks across the full available year", () => {
    const series = buildYearlySeries();
    const plan = buildChartTimeAxisPlan("1Y", series, 900);

    expect(plan.ticks.length).toBeGreaterThanOrEqual(10);
    const months = new Set(
      plan.ticks.map((tick) => tick.label.split(" ")[0]),
    );
    expect(months.size).toBeGreaterThanOrEqual(10);
    expect(plan.ticks[0].label).toMatch(/2025/);
    expect(plan.ticks[plan.ticks.length - 1].label).toMatch(/2026/);
    expect(plan.ticks.map((tick) => tick.label)).toContain("Aug 2025");
    expect(plan.ticks.map((tick) => tick.label)).toContain("Aug 2026");
  });

  it("duplicate timestamps do not produce duplicate visible labels", () => {
    const series: ChartSeriesPoint[] = [
      { t: istTimestamp(2025, 8, 18, 10, 0), v: 100 },
      { t: istTimestamp(2025, 8, 18, 10, 0), v: 101 },
      { t: istTimestamp(2025, 8, 18, 11, 0), v: 102 },
      { t: istTimestamp(2025, 8, 19, 10, 0), v: 103 },
    ];

    const labels = labelsFor("1W", series, 720);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("labels do not overlap beyond the chart intended tolerance", () => {
    const scenarios: Array<["1D" | "1W" | "1M" | "3M" | "1Y", ChartSeriesPoint[]]> =
      [
        ["1D", buildIntradayWeekSeries().slice(0, 26)],
        ["1W", buildIntradayWeekSeries()],
        ["1M", buildDailySeries({ year: 2025, month: 7, day: 25 }, 22)],
        ["3M", buildDailySeries({ year: 2025, month: 6, day: 2 }, 66)],
        ["1Y", buildYearlySeries()],
      ];

    scenarios.forEach(([timeframe, series]) => {
      const labels = labelsFor(timeframe, series, 600);
      expect(estimateTickLabelOverlap(timeframe, labels, 600)).toBe(false);
    });
  });

  it("different data ranges work correctly", () => {
    const shortSeries = buildDailySeries({ year: 2026, month: 1, day: 2 }, 8);
    const longSeries = buildDailySeries({ year: 2024, month: 3, day: 1 }, 120);

    const shortPlan = buildChartTimeAxisPlan("1M", shortSeries, 500);
    const longPlan = buildChartTimeAxisPlan("3M", longSeries, 500);

    expect(shortPlan.ticks.length).toBeGreaterThanOrEqual(2);
    expect(longPlan.ticks.length).toBeGreaterThan(longPlan.ticks.length > 0 ? 2 : 0);
    expect(shortPlan.tickValues[0]).toBe(shortSeries[0].t);
    expect(longPlan.tickValues[longPlan.tickValues.length - 1]).toBe(
      longSeries[longSeries.length - 1].t,
    );
  });

  it("missing weekends/market holidays do not break the timeline", () => {
    const series = buildDailySeries({ year: 2025, month: 8, day: 11 }, 10);
    const indices = selectChartXAxisTickIndices("1W", series, 720);

    expect(indices[0]).toBe(0);
    expect(indices[indices.length - 1]).toBe(series.length - 1);
    expect(indices.every((index) => index >= 0 && index < series.length)).toBe(
      true,
    );
  });

  it("future dates continue to work without hard-coded assumptions", () => {
    const series = buildDailySeries({ year: 2027, month: 2, day: 1 }, 45);
    const labels = labelsFor("3M", series, 720);

    expect(labels.length).toBeGreaterThan(2);
    expect(labels.every((label) => /^\d{2} \w{3}$/.test(label))).toBe(true);
    expect(labels.some((label) => label.includes("Feb"))).toBe(true);
    expect(labels.some((label) => label.includes("Mar"))).toBe(true);
  });
});
