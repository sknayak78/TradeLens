import {
  canRenderCandles,
  isCandleUsable,
  isBullish,
  computeEMASeries,
  buildEMAColumns,
  isEMAmeaningful,
  pickFirst,
  ohlcRange,
  candleYDomain,
  formatVolume,
  type EMAColumns,
} from "./candlestick";
import type { ChartSeriesPoint } from "@/types";

function candle(
  v: number,
  overrides: Partial<ChartSeriesPoint> = {},
): ChartSeriesPoint {
  return { t: "2026-08-01T09:15:00+05:30", v, o: v - 1, h: v + 2, l: v - 2, vol: 100, ...overrides };
}

describe("candlestick OHLC detection", () => {
  it("accepts a realistic candle", () => {
    expect(isCandleUsable(candle(100))).toBe(true);
  });

  it("rejects points that are missing OHLC fields", () => {
    expect(isCandleUsable({ t: "x", v: 100 })).toBe(false);
  });

  it("rejects degenerate candles (open==high==low==close) so the chart falls back", () => {
    expect(isCandleUsable({ t: "x", v: 100, o: 100, h: 100, l: 100 })).toBe(false);
  });

  it("rejects non-finite values", () => {
    expect(
      isCandleUsable({ t: "x", v: 100, o: Number.NaN, h: 105, l: 95 }),
    ).toBe(false);
  });

  it("canRenderCandles requires a high fraction of usable points", () => {
    expect(canRenderCandles([candle(100), candle(101)])).toBe(true);
    expect(canRenderCandles([candle(100), { t: "x", v: 101 }])).toBe(false);
    expect(canRenderCandles([])).toBe(false);
  });

  it("canRenderCandles tolerates a small minority of degenerate points", () => {
    const good = Array.from({ length: 10 }, (_, i) => candle(100 + i));
    // One flat/"seed" point out of eleven (~9%, below the 10% budget) must not
    // abort the candle view.
    const withOneFlat = [...good, { t: "x", v: 105, o: 105, h: 105, l: 105 }];
    expect(canRenderCandles(withOneFlat)).toBe(true);
    // A 50/50 mix must still fall back to the close line.
    const halfFlat = [...good, ...good.map(() => ({ t: "x", v: 0 }))];
    expect(canRenderCandles(halfFlat)).toBe(false);
  });
});

describe("candlestick direction", () => {
  it("marks a rising close as bullish a or equal open as neutral-bullish", () => {
    expect(isBullish(98, 100)).toBe(true);
    expect(isBullish(102, 100)).toBe(false);
    expect(isBullish(null, 100)).toBe(true);
  });
});

describe("EMA computation", () => {
  it("emits a value only once `period` observations have warmed up", () => {
    const ema = computeEMASeries([10, 11, 12, 13], 3);
    expect(ema).toEqual([null, null, 11, 12]);
  });

  it("returns null for every index when there are insufficient observations", () => {
    expect(computeEMASeries([100, 101, 102, 103], 20)).toEqual([
      null,
      null,
      null,
      null,
    ]);
  });

  it("does not count gaps toward the warm-up and preserves series length", () => {
    const ema = computeEMASeries([10, 11, null, 12, 13], 3);
    expect(ema).toHaveLength(5);
    expect(ema[0]).toBeNull();
    expect(ema[1]).toBeNull();
    expect(ema[2]).toBeNull();
    expect(ema[3]).toBeCloseTo(11);
    expect(ema[4]).toBeCloseTo(12);
  });

  it("returns all null for empty input or invalid period", () => {
    expect(computeEMASeries([], 20)).toEqual([]);
    expect(computeEMASeries([100, 101], 0)).toEqual([null, null]);
  });

  it("builds ema20/50/200 columns aligned to the series (with warm-up nulls)", () => {
    const series = [candle(100), candle(101, { t: "T2" }), candle(102, { t: "T3" })];
    const columns: EMAColumns = buildEMAColumns(series);
    expect(columns.ema20).toHaveLength(3);
    expect(columns.ema50).toHaveLength(3);
    expect(columns.ema200).toHaveLength(3);
    expect(columns.ema20).toEqual([null, null, null]);
  });
});

describe("EMA meaningfulness", () => {
  it("requires at least `period` observations before an EMA is meaningful", () => {
    expect(isEMAmeaningful(200, 200)).toBe(true);
    expect(isEMAmeaningful(252, 200)).toBe(true);
    expect(isEMAmeaningful(78, 20)).toBe(true);
    expect(isEMAmeaningful(22, 50)).toBe(false);
    expect(isEMAmeaningful(65, 200)).toBe(false);
    expect(isEMAmeaningful(5, 20)).toBe(false);
    expect(isEMAmeaningful(0, 20)).toBe(false);
  });
});

describe("candlestick helpers", () => {
  it("pickFirst returns the first finite value", () => {
    expect(pickFirst(null, undefined, 5, 7)).toBe(5);
    expect(pickFirst(null, null)).toBeNull();
  });

  it("backend EMA wins over the frontend fallback (pickFirst order)", () => {
    // Mirror of CandlestickChart's `pickFirst(point.ema20, localEmaColumns.ema20[i])`:
    // the backend value is always the FIRST argument and must never be overridden
    // by the fallback column (ER-0038 requirement 9).
    const backend = 700;
    const frontendFallback = 725;
    expect(pickFirst(backend, frontendFallback)).toBe(backend);
    expect(pickFirst(frontendFallback, backend)).toBe(frontendFallback);
    // The fallback may only fill a null backend value (null from backend, not this).
    expect(pickFirst(null, frontendFallback)).toBe(frontendFallback);
  });

  it("ohlcRange spans the full high/low range", () => {
    const range = ohlcRange([
      candle(100, { h: 110, l: 90 }),
      candle(101, { h: 115, l: 95 }),
    ]);
    expect(range).toEqual({ min: 90, max: 115 });
  });

  it("ohlcRange returns null for an empty series", () => {
    expect(ohlcRange([])).toBeNull();
  });

  it("formats volume with the Indian number format and an em dash when absent", () => {
    expect(formatVolume(1234567)).toBe("12,34,567");
    expect(formatVolume(null)).toBe("—");
    expect(formatVolume(undefined)).toBe("—");
  });
});

describe("candleYDomain", () => {
  const pivot = () => candle(500, { o: 490, h: 515, l: 485, v: 500 });

  it("anchors on the OHLC range with padding when indicators are absent", () => {
    const [min, max] = candleYDomain([pivot()], []);
    // span = 30 (515-485), pad = max(30*0.06, 30*0.002) = 1.8
    expect(min).toBeCloseTo(485 - 1.8, 5);
    expect(max).toBeCloseTo(515 + 1.8, 5);
  });

  it("folds in an indicator within the cushion", () => {
    const [min] = candleYDomain([pivot()], [480]);
    // 480 is within cushion = 30*0.35 = 10.5 of the OHLC low (485) -> included.
    expect(min).toBe(480);
  });

  it("clips a far-away indicator so it can never crush the candles", () => {
    const [min] = candleYDomain([pivot()], [200]);
    // 200 is far below the cushion (485 - 10.5 = 474.5); it must not drag the axis.
    expect(min).toBeCloseTo(485 - 1.8, 5);
  });

  it("does not extend upward beyond the cushion either", () => {
    const [min, max] = candleYDomain([pivot()], [900]);
    // 900 is far above; domain stays OHLC-anchored.
    expect(max).toBeCloseTo(515 + 1.8, 5);
    expect(min).toBeCloseTo(485 - 1.8, 5);
  });
});
