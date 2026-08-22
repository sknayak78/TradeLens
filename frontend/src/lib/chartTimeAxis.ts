/**
 * Chart X-axis tick selection and time-scale helpers.
 *
 * Spacing model:
 * - 1D/1W/1M/3M: trading-session spacing via categorical `t` axis (series order).
 * - 1Y: chronological spacing via numeric epoch-ms `x` axis so months sit at
 *   their true elapsed-time positions across the year.
 */
import {
  type ChartTimeframe,
  formatChartAxisTickLabel,
} from "@/lib/chartAxisFormat";

export type { ChartTimeframe };

export interface ChartSeriesPoint {
  t: string;
  v: number;
}

export interface ChartTimeAxisTick {
  index: number;
  timestamp: string;
  label: string;
  /** Epoch milliseconds for time-scaled axes. */
  x: number;
}

export interface ChartTimeAxisPlan {
  /** Selected ticks with formatted labels. */
  ticks: ChartTimeAxisTick[];
  /** ISO timestamp values for categorical Recharts `ticks` (non-1Y). */
  tickValues: string[];
  /** Epoch-ms tick positions for time-scaled Recharts `ticks` (1Y). */
  tickTimestamps: number[];
  /** Min/max epoch-ms domain for time-scaled axes (1Y). */
  timeDomain: [number, number] | null;
  /** When true, ChartCard renders a numeric/time XAxis on `x`. */
  useTimeScale: boolean;
  /** Series enriched with epoch-ms `x` for positioning. */
  series: Array<ChartSeriesPoint & { x: number }>;
}

interface TimeframeAxisConfig {
  minLabelWidthPx: number;
  targetTicks: number;
  maxTicks: number;
}

const IST = "Asia/Kolkata";

const TIMEFRAME_AXIS_CONFIG: Record<ChartTimeframe, TimeframeAxisConfig> = {
  "1D": { minLabelWidthPx: 44, targetTicks: 6, maxTicks: 8 },
  "1W": { minLabelWidthPx: 52, targetTicks: 5, maxTicks: 7 },
  "1M": { minLabelWidthPx: 52, targetTicks: 5, maxTicks: 7 },
  "3M": { minLabelWidthPx: 48, targetTicks: 8, maxTicks: 10 },
  "1Y": { minLabelWidthPx: 64, targetTicks: 12, maxTicks: 13 },
};

function parseTimestamp(isoTimestamp: string): Date {
  return new Date(isoTimestamp);
}

function toEpochMs(isoTimestamp: string): number {
  return parseTimestamp(isoTimestamp).getTime();
}

/** True when the chart should plot X by elapsed time rather than series index. */
export function usesTimeScale(timeframe: ChartTimeframe): boolean {
  return timeframe === "1Y";
}

/** Normalized [0,1] position by elapsed time for a series point index. */
export function getTimePositionRatio(
  series: ChartSeriesPoint[],
  index: number,
): number {
  if (series.length <= 1) {
    return 0;
  }
  const start = toEpochMs(series[0].t);
  const end = toEpochMs(series[series.length - 1].t);
  if (start === end) {
    return 0;
  }
  return (toEpochMs(series[index].t) - start) / (end - start);
}

/** Normalized [0,1] position by array index (categorical spacing). */
export function getIndexPositionRatio(length: number, index: number): number {
  if (length <= 1) {
    return 0;
  }
  return index / (length - 1);
}

export function isChronologicallyOrdered(series: ChartSeriesPoint[]): boolean {
  for (let index = 1; index < series.length; index += 1) {
    if (toEpochMs(series[index].t) < toEpochMs(series[index - 1].t)) {
      return false;
    }
  }
  return true;
}

function formatIstParts(date: Date): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
} {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);

  const read = (type: Intl.DateTimeFormatPartTypes): number => {
    const value = parts.find((part) => part.type === type)?.value ?? "0";
    return Number.parseInt(value, 10);
  };

  return {
    year: read("year"),
    month: read("month"),
    day: read("day"),
    hour: read("hour"),
    minute: read("minute"),
  };
}

function calendarDayKey(isoTimestamp: string): string {
  const { year, month, day } = formatIstParts(parseTimestamp(isoTimestamp));
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function calendarMonthKey(isoTimestamp: string): string {
  const { year, month } = formatIstParts(parseTimestamp(isoTimestamp));
  return `${year}-${String(month).padStart(2, "0")}`;
}

/** Monday-based ISO week key in IST (YYYY-Www). */
function isoWeekKey(isoTimestamp: string): string {
  const date = parseTimestamp(isoTimestamp);
  const { year, month, day } = formatIstParts(date);
  const utc = Date.UTC(year, month - 1, day);
  const weekday = new Date(utc).getUTCDay() || 7;
  const thursday = new Date(utc + (4 - weekday) * 86_400_000);
  const isoYear = thursday.getUTCFullYear();
  const yearStart = Date.UTC(isoYear, 0, 1);
  const week = Math.ceil(((thursday.getTime() - yearStart) / 86_400_000 + 1) / 7);
  return `${isoYear}-W${String(week).padStart(2, "0")}`;
}

function uniqueSorted(indices: number[]): number[] {
  return [...new Set(indices)].sort((a, b) => a - b);
}

function clampTickCount(
  timeframe: ChartTimeframe,
  chartWidthPx: number,
): number {
  const config = TIMEFRAME_AXIS_CONFIG[timeframe];
  const widthLimited = Math.max(
    2,
    Math.floor(chartWidthPx / config.minLabelWidthPx),
  );
  return Math.min(config.maxTicks, Math.max(2, Math.min(config.targetTicks, widthLimited)));
}

function selectFirstIndexPerBucket(
  series: ChartSeriesPoint[],
  bucketKey: (isoTimestamp: string) => string,
): number[] {
  const indices: number[] = [];
  let lastBucket: string | null = null;

  series.forEach((point, index) => {
    const bucket = bucketKey(point.t);
    if (bucket !== lastBucket) {
      indices.push(index);
      lastBucket = bucket;
    }
  });

  return indices;
}

function selectEvenlySpacedByTime(
  series: ChartSeriesPoint[],
  desiredCount: number,
): number[] {
  if (series.length <= desiredCount) {
    return series.map((_, index) => index);
  }

  const times = series.map((point) => toEpochMs(point.t));
  const start = times[0];
  const end = times[times.length - 1];
  if (start === end) {
    return [0, series.length - 1];
  }

  const indices: number[] = [0];
  for (let tick = 1; tick < desiredCount - 1; tick += 1) {
    const target = start + ((end - start) * tick) / (desiredCount - 1);
    let bestIndex = 0;
    let bestDistance = Number.POSITIVE_INFINITY;
    for (let index = 0; index < times.length; index += 1) {
      const distance = Math.abs(times[index] - target);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = index;
      }
    }
    indices.push(bestIndex);
  }
  indices.push(series.length - 1);
  return uniqueSorted(indices);
}

function thinIndices(indices: number[], maxCount: number): number[] {
  if (indices.length <= maxCount) {
    return indices;
  }
  if (maxCount <= 1) {
    return [indices[0]];
  }

  const thinned: number[] = [];
  for (let i = 0; i < maxCount; i += 1) {
    const position = Math.round((i * (indices.length - 1)) / (maxCount - 1));
    thinned.push(indices[position]);
  }
  return uniqueSorted(thinned);
}

function dedupeByRenderedLabel(
  timeframe: ChartTimeframe,
  series: ChartSeriesPoint[],
  indices: number[],
): number[] {
  const deduped: number[] = [];
  let lastLabel: string | null = null;

  indices.forEach((index) => {
    const label = formatChartAxisTickLabel(timeframe, series[index].t);
    if (label !== lastLabel) {
      deduped.push(index);
      lastLabel = label;
    }
  });

  return deduped;
}

function ensureEdgeIndices(indices: number[], lastIndex: number): number[] {
  const withEdges = uniqueSorted([0, ...indices, lastIndex]);
  return withEdges;
}

/**
 * Select representative tick indices for a timeframe and series.
 */
export function selectChartXAxisTickIndices(
  timeframe: ChartTimeframe,
  series: ChartSeriesPoint[],
  chartWidthPx = 600,
): number[] {
  if (!series.length) {
    return [];
  }
  if (series.length === 1) {
    return [0];
  }

  const maxTicks = clampTickCount(timeframe, chartWidthPx);
  const lastIndex = series.length - 1;
  let indices: number[];

  switch (timeframe) {
    case "1D":
      indices = selectEvenlySpacedByTime(series, maxTicks);
      break;
    case "1W":
      indices = selectFirstIndexPerBucket(series, calendarDayKey);
      indices = thinIndices(indices, maxTicks);
      break;
    case "1M":
      indices = selectEvenlySpacedByTime(series, maxTicks);
      break;
    case "3M":
      indices = selectFirstIndexPerBucket(series, isoWeekKey);
      indices = thinIndices(indices, maxTicks);
      break;
    case "1Y":
      indices = selectFirstIndexPerBucket(series, calendarMonthKey);
      indices = thinIndices(indices, maxTicks);
      break;
    default:
      indices = selectEvenlySpacedByTime(series, maxTicks);
  }

  indices = ensureEdgeIndices(indices, lastIndex);
  indices = dedupeByRenderedLabel(timeframe, series, indices);

  if (indices.length > maxTicks) {
    const middle = indices.slice(1, -1);
    const allowedMiddle = maxTicks - 2;
    const thinnedMiddle =
      allowedMiddle > 0 ? thinIndices(middle, allowedMiddle) : [];
    indices = dedupeByRenderedLabel(
      timeframe,
      series,
      uniqueSorted([0, ...thinnedMiddle, lastIndex]),
    );
  }

  return indices;
}

/**
 * Build tick metadata and enriched series for chart rendering.
 */
export function buildChartTimeAxisPlan(
  timeframe: ChartTimeframe,
  series: ChartSeriesPoint[],
  chartWidthPx = 600,
): ChartTimeAxisPlan {
  const enrichedSeries = series.map((point) => ({
    ...point,
    x: toEpochMs(point.t),
  }));

  const indices = selectChartXAxisTickIndices(timeframe, series, chartWidthPx);
  const ticks: ChartTimeAxisTick[] = indices.map((index) => ({
    index,
    timestamp: series[index].t,
    label: formatChartAxisTickLabel(timeframe, series[index].t),
    x: enrichedSeries[index].x,
  }));

  const useTimeScale = usesTimeScale(timeframe);
  const timeDomain: [number, number] | null =
    useTimeScale && enrichedSeries.length
      ? [enrichedSeries[0].x, enrichedSeries[enrichedSeries.length - 1].x]
      : null;

  return {
    ticks,
    tickValues: useTimeScale ? [] : ticks.map((tick) => tick.timestamp),
    tickTimestamps: useTimeScale ? ticks.map((tick) => tick.x) : [],
    timeDomain,
    useTimeScale,
    series: enrichedSeries,
  };
}

/**
 * Format a tick label for the chart axis (used by Recharts tickFormatter).
 */
export function formatChartXAxisTickLabel(
  timeframe: ChartTimeframe,
  isoTimestampOrEpoch: string | number,
): string {
  if (typeof isoTimestampOrEpoch === "number") {
    return formatChartAxisTickLabel(
      timeframe,
      new Date(isoTimestampOrEpoch).toISOString(),
    );
  }
  return formatChartAxisTickLabel(timeframe, isoTimestampOrEpoch);
}

/**
 * Estimate whether visible tick labels would overlap at a given chart width.
 * Useful for regression tests; not a pixel-perfect layout measurement.
 */
export function estimateTickLabelOverlap(
  timeframe: ChartTimeframe,
  labels: string[],
  chartWidthPx: number,
): boolean {
  if (labels.length <= 1) {
    return false;
  }
  const minLabelWidth = TIMEFRAME_AXIS_CONFIG[timeframe].minLabelWidthPx;
  const requiredWidth = labels.length * minLabelWidth;
  return requiredWidth > chartWidthPx * 1.05;
}
