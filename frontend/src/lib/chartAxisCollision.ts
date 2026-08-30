import type { ChartTimeAxisTick } from "@/lib/chartTimeAxis";
import {
  calendarDayKey,
  calendarMonthKey,
  isoWeekKey,
} from "@/lib/chartTimeAxis";
import type { XAxisLabelPresentation } from "@/lib/chartAxisFormat";
import { formatChartAxisTickLabel } from "@/lib/chartAxisFormat";

const CHAR_WIDTH_RATIO = 0.6;
const FONT_SIZE = 10;
const LABEL_GAP_PX = 6;
const Y_AXIS_WIDTH = 50;

export type ChartTimeframe = "1D" | "1W" | "1M" | "3M" | "1Y";

export interface XAxisEdgeMargins {
  left: number;
  right: number;
}

interface FilterScenario {
  timeframe: ChartTimeframe;
  ticks: ChartTimeAxisTick[];
  useTimeScale: boolean;
  timeDomain: [number, number] | null;
  seriesLength: number;
  plotWidthPx: number;
  presentation: XAxisLabelPresentation;
  /**
   * Full series timestamps ({ t, x }) so the selector can build a dense,
   * semantically meaningful candidate pool before picking the final subset.
   * When absent, the passed ticks are used directly as the candidate pool.
   */
  series?: Array<{ t: string; x?: number }>;
}

/**
 * Readable label-count targets per timeframe. The actual selected count may be
 * lower when the plot width or the candidate availability cannot support it.
 */
const TARGET_TICK_COUNT: Record<ChartTimeframe, number> = {
  "1D": 7,
  "1W": 7,
  "1M": 6,
  "3M": 8,
  "1Y": 10,
};

function epochMs(ts: string): number {
  return new Date(ts).getTime();
}

/** Horizontal footprint (px) of a rotated label drawn at a given angle. */
export function estimateRotatedLabelWidth(
  label: string,
  fontSize: number,
  angle: number,
): number {
  if (label.length === 0) return 0;
  const textWidth = label.length * CHAR_WIDTH_RATIO * fontSize;
  const rad = (angle * Math.PI) / 180;
  return Math.abs(textWidth * Math.cos(rad)) +
    Math.abs(fontSize * Math.sin(rad));
}

/**
 * Candidate tick text width for the collision pass. Falls back to the raw
 * stamp (e.g. "2025-08-21T09:15:00+05:30") when no short label is available;
 * uses the *shortest* plausible label to avoid over-aggressive filtering.
 */
function tickLabelForSizing(tick: ChartTimeAxisTick): string {
  const raw = tick.label ?? String(tick.timestamp);
  const match = raw.match(/(?:20\d\d[-\/]?)?(\d{1,2})[-\/](\d{2}|[A-Za-z]{3})/);
  if (!match) return raw;
  const short = match[2];
  if (/^[A-Za-z]{3}$/.test(short)) return `${short} ${match[1]}`;
  return short;
}

/** Position (px from plot-left) mirroring Recharts' coordinate mapping. */
function tickPosition(
  scenario: Pick<
    FilterScenario,
    "useTimeScale" | "timeDomain" | "seriesLength" | "plotWidthPx"
  >,
  tick: ChartTimeAxisTick,
): number {
  const { useTimeScale, timeDomain, seriesLength, plotWidthPx } = scenario;
  if (useTimeScale && timeDomain) {
    const span = timeDomain[1] - timeDomain[0];
    if (span <= 0) return 0;
    return ((tick.x - timeDomain[0]) / span) * plotWidthPx;
  }
  if (seriesLength <= 1) return 0;
  return (tick.index / (seriesLength - 1)) * plotWidthPx;
}

/** First index of each distinct bucket, in chronological order. */
function firstIndexPerBucket(
  series: Array<{ t: string }>,
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

/** Indices belonging to the most recent (last) trading session for 1D. */
function lastSessionIndices(
  series: Array<{ t: string }>,
): number[] {
  if (series.length === 0) return [];
  const lastKey = calendarDayKey(series[series.length - 1].t);
  const indices: number[] = [];
  series.forEach((point, index) => {
    if (calendarDayKey(point.t) === lastKey) indices.push(index);
  });
  return indices;
}

/** Dedupe by rendered label, keeping the LAST occurrence (true end wins). */
function dedupeByLabelKeepLast(
  timeframe: ChartTimeframe,
  series: Array<{ t: string }>,
  indices: number[],
): number[] {
  const seenLabels = new Set<string>();
  const result: number[] = [];
  for (let i = indices.length - 1; i >= 0; i -= 1) {
    const label = formatChartAxisTickLabel(timeframe, series[indices[i]].t);
    if (!seenLabels.has(label)) {
      seenLabels.add(label);
      result.push(indices[i]);
    }
  }
  result.reverse();
  return result;
}

/**
 * Build a dense, semantically meaningful candidate index pool from the full
 * series. This mirrors buildChartTimeAxisPlan's per-timeframe bucketing but
 * WITHOUT the hard max-tick thinning, so the final distribution decision is
 * deferred to the pixel-based selection stage.
 */
function buildCandidateIndices(
  timeframe: ChartTimeframe,
  series: Array<{ t: string }>,
): number[] {
  if (series.length === 0) return [];
  const lastIndex = series.length - 1;
  const first = 0;

  let middle: number[];
  switch (timeframe) {
    case "1D":
      // Restrict to the latest trading session, dropping any leading
      // previous-session fragment so the axis begins at the session open.
      return lastSessionIndices(series);
    case "1W":
      middle = firstIndexPerBucket(series, calendarDayKey);
      break;
    case "1M":
      // Monthly series are daily points; treat every point as a candidate.
      middle = series.map((_, index) => index);
      break;
    case "3M":
      middle = firstIndexPerBucket(series, isoWeekKey);
      break;
    case "1Y":
      middle = firstIndexPerBucket(series, calendarMonthKey);
      break;
    default:
      middle = series.map((_, index) => index);
  }

  // Anchor the true series endpoints, then dedupe by rendered label keeping
  // the LAST occurrence (so the end-of-range tick wins over an intermediate
  // first-of-last-bucket candidate with the same label).
  const withEdges = [first, ...middle, lastIndex].sort((a, b) => a - b);
  return dedupeByLabelKeepLast(timeframe, series, withEdges);
}

/**
 * Select a subset of ordered candidates that is (a) non-overlapping and
 * (b) as evenly distributed across the range as possible, always anchoring the
 * first and last (end-of-range) ticks.
 *
 * Candidates are assumed to be semantically meaningful (per intraday bar, per
 * day/week/month boundary) and therefore already roughly even in time. We pick
 * a uniformly spaced subset in candidate-index space, then strip any adjacent
 * picks that would collide — because the pool is dense, stripping one candidate
 * leaves only a small gap, never a large hole.
 */
function selectEvenDistributed(
  positions: number[],
  footprints: number[],
  targetCount: number,
): number[] {
  const m = positions.length;
  if (m === 0) return [];
  if (m === 1) return [0];

  const target = Math.max(2, Math.min(targetCount, m));
  const picks: number[] = [];
  for (let k = 0; k < target; k += 1) {
    const idx = Math.round((k * (m - 1)) / (target - 1));
    if (picks[picks.length - 1] !== idx) picks.push(idx);
  }
  if (picks[0] !== 0) picks[0] = 0;
  if (picks[picks.length - 1] !== m - 1) picks.push(m - 1);

  // Strip collisions left→right, preferring to keep the earlier tick.
  const kept: number[] = [picks[0]];
  let lastPos = positions[picks[0]];
  for (let i = 1; i < picks.length - 1; i += 1) {
    const idx = picks[i];
    if (positions[idx] - lastPos >= footprints[idx] + LABEL_GAP_PX) {
      kept.push(idx);
      lastPos = positions[idx];
    }
  }

  // Anchor the end-of-range tick, dropping recent kept ticks that collide.
  while (
    kept.length > 1 &&
    positions[m - 1] - positions[kept[kept.length - 1]] <
      footprints[m - 1] + LABEL_GAP_PX
  ) {
    kept.pop();
  }
  if (kept[kept.length - 1] !== m - 1) kept.push(m - 1);

  return kept;
}

/**
 * Select the X-axis ticks to render: builds a dense semantic candidate pool
 * from the series (or uses the provided ticks), then picks an evenly
 * distributed, non-overlapping subset anchored at the session/range ends.
 * Keeps chartTimeAxis/buildChartTimeAxisPlan semantics untouched.
 */
export function filterCollidingXAxisTicks(
  input: FilterScenario,
): ChartTimeAxisTick[] {
  const { timeframe, ticks, presentation, series } = input;

  // Build the candidate pool. Prefer a dense semantic pool from the full
  // series; fall back to the provided ticks (e.g. pure unit-test callers).
  let candidates: ChartTimeAxisTick[];
  if (series && series.length) {
    const indices = buildCandidateIndices(timeframe, series);
    candidates = indices.map((index) => ({
      index,
      timestamp: series[index].t,
      label: formatChartAxisTickLabel(timeframe, series[index].t),
      x: series[index].x ?? epochMs(series[index].t),
    }));
  } else {
    candidates = ticks;
  }
  if (candidates.length === 0) return [];
  if (candidates.length === 1) return candidates;

  const positions = candidates.map((t) => tickPosition(input, t));
  const footprints = candidates.map((t) =>
    estimateRotatedLabelWidth(tickLabelForSizing(t), FONT_SIZE, presentation.angle),
  );

  const selected = selectEvenDistributed(
    positions,
    footprints,
    TARGET_TICK_COUNT[timeframe],
  );

  return selected.map((i) => candidates[i]);
}

/**
 * Modest left/right chart margins that reserve breathing room so the first and
 * last angled labels do not clip at the plot edges.
 */
export function getXAxisEdgeMargins(
  timeframe: ChartTimeframe,
): XAxisEdgeMargins {
  const table: Record<ChartTimeframe, XAxisEdgeMargins> = {
    "1D": { left: 14, right: 18 },
    "1W": { left: 16, right: 20 },
    "1M": { left: 16, right: 18 },
    "3M": { left: 16, right: 18 },
    "1Y": { left: 18, right: 22 },
  };
  return table[timeframe];
}

/** Convenience: derive the effective plot width a chart renders into. */
export function computePlotWidthPx(
  chartWidth: number,
  timeframe: ChartTimeframe,
): number {
  const m = getXAxisEdgeMargins(timeframe);
  return Math.max(1, chartWidth - m.left - m.right - Y_AXIS_WIDTH);
}
