/**
 * Pure helpers for rendering a candlestick price chart from a stock series.
 *
 * A series point always carries `t` (timestamp) and `v` (close). Candlestick
 * rendering additionally needs `o`/`h`/`l` (open/high/low) and optionally
 * `vol` (volume). When those fields are missing or degenerate (open == high ==
 * low == close, as produced by fallback providers), the chart falls back to a
 * simple close line rather than fabricating OHLC values.
 */
import type { ChartSeriesPoint } from "@/types";

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isDegenerate(
  o: number,
  h: number,
  l: number,
  c: number,
): boolean {
  return Math.abs(o - c) < 1e-9 && Math.abs(h - c) < 1e-9 && Math.abs(l - c) < 1e-9;
}

/** True when a single point carries finite, non-degenerate OHLC for a candle. */
export function isCandleUsable(point: ChartSeriesPoint): boolean {
  const { o, h, l, v } = point;
  if (!isFiniteNumber(o) || !isFiniteNumber(h) || !isFiniteNumber(l) || !isFiniteNumber(v)) {
    return false;
  }
  return !isDegenerate(o, h, l, v);
}

/** Fraction of points that carry a real (non-degenerate) OHLC for a candle. */
export function candleUsableFraction(series: ChartSeriesPoint[]): number {
  if (!series.length) return 0;
  let usable = 0;
  for (const point of series) {
    if (isCandleUsable(point)) usable += 1;
  }
  return usable / series.length;
}

/**
 * True when the series has enough real candles to draw meaningfully. Uses a
 * high-threshold fraction rather than requiring every single point: a handful
 * of degenerate points (e.g. a seed provider's flat bars) must not abort the
 * whole candle view. The unused points are simply skipped by CandleShape.
 */
export function canRenderCandles(series: ChartSeriesPoint[]): boolean {
  if (!series.length) return false;
  return candleUsableFraction(series) >= 0.9;
}

/** Emoji-neutral helper used by the tooltip to label candle direction. */
export function isBullish(o: number | null | undefined, c: number): boolean {
  if (!isFiniteNumber(o)) return c >= c;
  return c >= o;
}

/**
 * EMA over closes with a proper warm-up: a value is only emitted once at least
 * `period` valid observations have accumulated, seeded by their simple average.
 * This keeps an EMA from implying it is meaningful before it has seen enough
 * data (e.g. an EMA200 must not be drawn from a handful of intraday bars).
 *
 * FALLBACK-ONLY (ER-0038): the backend (`backend/indicators/ema.py` `compute_ema`,
 * served per-candle on the chart series) is the authoritative EMA source. This
 * mirror is used solely to fill candles the backend left null (e.g. seed/sparse
 * fallback); it must never run when a valid backend value is present. Callers
 * must apply it via `pickFirst(backendValue, thisValue)` so the backend wins.
 */
export function computeEMASeries(
  closes: Array<number | null | undefined>,
  period: number,
): Array<number | null> {
  const out: Array<number | null> = closes.map(() => null);
  if (period <= 0) {
    return out;
  }
  const k = 2 / (period + 1);
  let seen = 0;
  let seedSum = 0;
  let prev = 0;
  for (let i = 0; i < closes.length; i += 1) {
    const value = closes[i];
    if (!isFiniteNumber(value)) {
      continue;
    }
    if (seen < period) {
      seedSum += value;
      seen += 1;
      if (seen === period) {
        prev = seedSum / period;
        out[i] = prev;
      }
      continue;
    }
    prev = value * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

/**
 * Minimum number of observations required for an EMA period to be meaningful.
 * Rendered EMA overlays should not appear before this threshold.
 */
export const EMA_MIN_OBSERVATIONS: Record<number, number> = {
  20: 20,
  50: 50,
  200: 200,
};

/**
 * True when a series has enough observations for an EMA of the given period to
 * be meaningful, so the chart does not imply an EMA200 from a short history.
 */
export function isEMAmeaningful(
  seriesLength: number,
  period: number,
): boolean {
  return isFiniteNumber(seriesLength) && seriesLength >= period;
}

export interface EMAColumns {
  ema20: Array<number | null>;
  ema50: Array<number | null>;
  ema200: Array<number | null>;
}

/** Compute EMA20/50/200 columns aligned to the series indexes. */
export function buildEMAColumns(
  series: ChartSeriesPoint[],
): EMAColumns {
  const closes = series.map((p) => p.v);
  return {
    ema20: computeEMASeries(closes, 20),
    ema50: computeEMASeries(closes, 50),
    ema200: computeEMASeries(closes, 200),
  };
}

/** Merge two aligned nullable numeric columns by preferring the first value. */
export function pickFirst(
  ...values: Array<number | null | undefined>
): number | null {
  for (const value of values) {
    if (isFiniteNumber(value)) return value;
  }
  return null;
}

export interface OHLCRange {
  min: number;
  max: number;
}

/** Full high/low span across the series, used for the Y-axis domain. */
export function ohlcRange(series: ChartSeriesPoint[]): OHLCRange | null {
  if (!series.length) return null;
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (const point of series) {
    const candidates = [point.l, point.h, point.v];
    for (const value of candidates) {
      if (isFiniteNumber(value)) {
        if (value < min) min = value;
        if (value > max) max = value;
      }
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
  return { min, max };
}

export interface CandleYDomainOptions {
  /** Fraction of the OHLC span added as headroom each side (default 0.06). */
  padRatio?: number;
  /** Max fraction of the OHLC span an indicator may pull the domain outward. */
  cushionRatio?: number;
}

/**
 * Y-domain that keeps price action dominant while keeping near indicators
 * visible. The axis is anchored on the visible OHLC range (plus `padRatio`
 * headroom); indicator values (EMA overlays) are folded in only if they lie
 * within a bounded `cushionRatio` of the OHLC range. A far-away indicator
 * (e.g. a deeply lagging EMA200 in a strong trend) is clipped instead of
 * stretching the axis and crushing the candles; it stays available in the
 * legend/tooltip and re-renders wherever it crosses back into range.
 */
export function candleYDomain(
  series: ChartSeriesPoint[],
  overlayValues: Array<number | null | undefined>,
  options: CandleYDomainOptions = {},
): [number, number] | undefined {
  const range = ohlcRange(series);
  if (!range || range.min === range.max) return undefined;
  const span = range.max - range.min;
  const padRatio = options.padRatio ?? 0.06;
  const cushionRatio = options.cushionRatio ?? 0.35;
  const pad = Math.max(span * padRatio, span * 0.002);
  const cushion = span * cushionRatio;
  let min = range.min - pad;
  let max = range.max + pad;
  for (const value of overlayValues) {
    if (!isFiniteNumber(value)) continue;
    if (value < min && value >= range.min - cushion) min = value;
    if (value > max && value <= range.max + cushion) max = value;
  }
  return [min, max];
}

/** Human-friendly tooltip label for a volume value (or em dash when absent). */
export function formatVolume(volume: number | null | undefined): string {
  return isFiniteNumber(volume) ? Number(volume).toLocaleString("en-IN") : "—";
}
