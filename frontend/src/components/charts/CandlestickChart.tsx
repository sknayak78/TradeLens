import { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import {
  buildChartTimeAxisPlan,
  formatChartXAxisTickLabel,
  type ChartTimeframe,
} from "@/lib/chartTimeAxis";
import {
  formatChartTooltipLabel,
  getXAxisLabelPresentation,
} from "@/lib/chartAxisFormat";
import {
  filterCollidingXAxisTicks,
  getXAxisEdgeMargins,
} from "@/lib/chartAxisCollision";
import {
  canRenderCandles,
  buildEMAColumns,
  candleYDomain,
  formatVolume,
  pickFirst,
  type EMAColumns,
} from "@/lib/candlestick";
import type { ChartSeriesPoint } from "@/types";

/** Human-readable bar interval for the selected timeframe (data-side config). */
const TIMEFRAME_INTERVAL_LABEL: Record<ChartTimeframe, string> = {
  "1D": "5m",
  "1W": "30m",
  "1M": "1D",
  "3M": "1D",
  "1Y": "1D",
};

/** EMA periods rendered as overlays, in draw order. */
const EMA_PERIODS = [20, 50, 200] as const;
type EMAPeriod = (typeof EMA_PERIODS)[number];

const EMA_COLORS: Record<EMAPeriod, string> = {
  20: "#2962ff",
  50: "#f59e0b",
  200: "#8b5cf6",
} as const;

const SUPPORT_COLOR = "#26a69a";
const RESISTANCE_COLOR = "#ef5350";
const UP_COLOR = "#26a69a";
const DOWN_COLOR = "#ef5350";
const FLAT_COLOR = "#2962ff";

interface CandlestickChartProps {
  series: ChartSeriesPoint[];
  timeframe: ChartTimeframe;
  support?: number | null;
  resistance?: number | null;
  lineColor?: string;
  heightClass?: string;
}

interface TooltipPoint extends ChartSeriesPoint {
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ payload?: TooltipPoint }>;
  timeframe: string;
  periods: number[];
}

/**
 * Shared OHLCV candle chart used by both Dashboard and Guided Research.
 *
 * Single source of truth for chart behaviour: candlesticks (with a graceful
 * close-line fallback when OHLC is genuinely unavailable or degenerate), the
 * EMA20/50/200 overlays, the support/resistance reference lines, the ER-0031
 * time axis, and the shared OHLCV/EMA tooltip.
 *
 * The surrounding page UX (timeframe controls, headers, panels) stays with
 * each caller; this component only owns the plot.
 */
export default function CandlestickChart({
  series,
  timeframe,
  support,
  resistance,
  lineColor,
  heightClass = "h-52 md:h-60 min-h-[220px] w-full -mx-2 relative",
}: CandlestickChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    const node = chartRef.current;
    if (!node) return undefined;
    const update = () => {
      const w = node.getBoundingClientRect().width;
      if (w > 0) setWidth(w);
    };
    update();
    const obs = new ResizeObserver(update);
    obs.observe(node);
    return () => obs.disconnect();
  }, [series]);

  const chartAxisPlan = useMemo(() => {
    if (!series?.length) return null;
    return buildChartTimeAxisPlan(timeframe, series, width);
  }, [timeframe, width, series]);

  // Angled X-axis label presentation (a rendering concern only; tick selection
  // stays in chartTimeAxis).
  const xAxisLabel = useMemo(
    () => getXAxisLabelPresentation(timeframe),
    [timeframe],
  );

  // Collision-aware presentation: filter the candidate ticks (from
  // buildChartTimeAxisPlan) down to the ones that fit without horizontal
  // overlap at the current plot width, and reserve edge breathing room.
  const edgeMargins = useMemo(() => getXAxisEdgeMargins(timeframe), [timeframe]);
  const yAxisWidth = 50;
  const plotWidthPx = Math.max(1, width - edgeMargins.left - edgeMargins.right - yAxisWidth);

  const filteredAxisTicks = useMemo(() => {
    if (!chartAxisPlan?.ticks?.length || !chartAxisPlan.series?.length) {
      return chartAxisPlan;
    }
    const filtered = filterCollidingXAxisTicks({
      timeframe,
      ticks: chartAxisPlan.ticks,
      useTimeScale: chartAxisPlan.useTimeScale,
      timeDomain: chartAxisPlan.timeDomain,
      seriesLength: chartAxisPlan.series.length,
      plotWidthPx,
      presentation: xAxisLabel,
      series: chartAxisPlan.series,
    });
    return {
      ...chartAxisPlan,
      ticks: filtered,
      tickValues: chartAxisPlan.useTimeScale
        ? []
        : filtered.map((t) => t.timestamp),
      tickTimestamps: chartAxisPlan.useTimeScale
        ? filtered.map((t) => t.x)
        : [],
    };
  }, [chartAxisPlan, timeframe, plotWidthPx, xAxisLabel]);

  const candlesUsable = useMemo(
    () => canRenderCandles(series ?? []),
    [series],
  );

  // Raw backend-agnostic warm-up columns (used only when the backend did not
  // supply a usable per-point EMA over its longer historical lookback).
  const localEmaColumns: EMAColumns = useMemo(
    () => buildEMAColumns(series ?? []),
    [series],
  );

  const chartData = useMemo(() => {
    const base = chartAxisPlan?.series ?? series ?? [];
    // Prefer EMA values emitted by the backend (computed over lookback reaching
    // beyond the visible window, e.g. EMA200 for a weekly 1Y view); fall back to
    // the frontend warm-up column only where the backend left a point null.
    return base.map((point, index) => ({
      ...point,
      ema20: pickFirst(
        (point as TooltipPoint).ema20,
        localEmaColumns.ema20[index],
      ) ?? undefined,
      ema50: pickFirst(
        (point as TooltipPoint).ema50,
        localEmaColumns.ema50[index],
      ) ?? undefined,
      ema200: pickFirst(
        (point as TooltipPoint).ema200,
        localEmaColumns.ema200[index],
      ) ?? undefined,
    }));
  }, [chartAxisPlan, series, localEmaColumns]);

  // Only include an EMA once there is an actual renderable value in the visible
  // window. When the data genuinely cannot support an EMA period (e.g. EMA200
  // from a short intraday history, or an all-null backend column) the overlay
  // and its legend/tooltip entry are omitted entirely — an explicit
  // "insufficient data" indication rather than a silent dotted dash.
  const meaningfulEMAs = useMemo(() => {
    return EMA_PERIODS.filter((period) => {
      const key = `ema${period}` as keyof TooltipPoint;
      return chartData.some((point) => isFiniteNumber(point[key]));
    });
  }, [chartData]);

  // Y domain is driven by the visible OHLC high/low so candle wicks use the
  // available plot height naturally. EMA overlays are folded in only within a
  // bounded cushion of the price range (see candleYDomain), so a close indicator
  // stays visible but a far-away one (e.g. a deeply lagging EMA200 in a strong
  // trend) can never stretch the axis and crush the candles. Support/resistance
  // are intentionally excluded: far levels would crush the candles, so they are
  // drawn as subordinate ReferenceLines instead.
  const yDomain = useMemo(() => {
    const overlays: Array<number | null | undefined> = [];
    for (const point of chartData) {
      overlays.push(point.ema20, point.ema50, point.ema200);
    }
    return candleYDomain(series ?? [], overlays);
  }, [series, chartData]);

  // Recharts 3.x no longer passes an axis scale to custom Bar shape functions.
  // We hand the shape the same Y-domain lower bound that the YAxis uses so the
  // candle geometry can be reconstructed from the close bar's pixel geometry.
  const candleData = useMemo(() => {
    if (!candlesUsable || !yDomain) return chartData;
    const domainMin = yDomain[0];
    return chartData.map((point) => ({ ...point, candleDomain: domainMin }));
  }, [chartData, candlesUsable, yDomain]);

  const legendItems = useMemo(() => {
    const items: Array<{ label: string; color: string; dashed?: boolean }> = [];
    if (candlesUsable) {
      for (const period of meaningfulEMAs) {
        items.push({
          label: `EMA${period}`,
          color: EMA_COLORS[period],
          dashed: period === 200,
        });
      }
    }
    if (isFiniteNumber(support)) {
      items.push({ label: "S", color: SUPPORT_COLOR, dashed: true });
    }
    if (isFiniteNumber(resistance)) {
      items.push({ label: "R", color: RESISTANCE_COLOR, dashed: true });
    }
    return items;
  }, [candlesUsable, meaningfulEMAs, support, resistance]);

  return (
    <div
      ref={chartRef}
      className={`${heightClass} relative`}
      data-testid="candlestick-chart"
    >
      <ChartLegend
        intervalLabel={`${TIMEFRAME_INTERVAL_LABEL[timeframe]} · ${timeframe}`}
        items={legendItems}
      />
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={candleData}
          margin={{
            top: 8,
            right: edgeMargins.right,
            bottom: 8,
            left: edgeMargins.left,
          }}
        >
          <CartesianGrid
            stroke="var(--tl-border)"
            strokeDasharray="2 4"
            vertical={false}
          />
          {filteredAxisTicks?.useTimeScale ? (
            <XAxis
              dataKey="x"
              type="number"
              scale="time"
              domain={filteredAxisTicks.timeDomain ?? ["dataMin", "dataMax"]}
              stroke="var(--tl-text-muted)"
              tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
              angle={xAxisLabel.angle}
              textAnchor={xAxisLabel.textAnchor}
              dy={xAxisLabel.dy}
              tickLine={false}
              axisLine={false}
              ticks={filteredAxisTicks.tickTimestamps}
              interval={0}
              height={xAxisLabel.height}
              tickFormatter={(value) =>
                formatChartXAxisTickLabel(timeframe, Number(value))
              }
            />
          ) : (
            <XAxis
              dataKey="t"
              stroke="var(--tl-text-muted)"
              tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
              angle={xAxisLabel.angle}
              textAnchor={xAxisLabel.textAnchor}
              dy={xAxisLabel.dy}
              tickLine={false}
              axisLine={false}
              ticks={filteredAxisTicks?.tickValues}
              interval={0}
              height={xAxisLabel.height}
              tickFormatter={(value) =>
                formatChartXAxisTickLabel(timeframe, String(value))
              }
            />
          )}
          <YAxis
            stroke="var(--tl-text-muted)"
            tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={false}
            domain={
              candlesUsable && yDomain
                ? yDomain
                : ["dataMin - 5", "dataMax + 5"]
            }
            width={50}
          />
          <Tooltip
            content={
              <ChartTooltip timeframe={timeframe} periods={meaningfulEMAs} />
            }
          />
          {isFiniteNumber(support) && (
            <ReferenceLine
              y={support as number}
              stroke={SUPPORT_COLOR}
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: "S",
                fill: SUPPORT_COLOR,
                fontSize: 10,
                position: "insideLeft",
              }}
            />
          )}
          {isFiniteNumber(resistance) && (
            <ReferenceLine
              y={resistance as number}
              stroke={RESISTANCE_COLOR}
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: "R",
                fill: RESISTANCE_COLOR,
                fontSize: 10,
                position: "insideLeft",
              }}
            />
          )}
          {candlesUsable ? (
            <>
              <Bar
                dataKey="v"
                shape={CandleShape}
                isAnimationActive={false}
                barSize="100%"
              />
              {meaningfulEMAs.map((period) => (
                <Line
                  key={`ema${period}`}
                  type="monotone"
                  dataKey={`ema${period}`}
                  stroke={EMA_COLORS[period]}
                  strokeWidth={1}
                  strokeOpacity={0.8}
                  strokeDasharray={period === 200 ? "4 3" : undefined}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
              ))}
            </>
          ) : (
            <Line
              type="monotone"
              dataKey="v"
              stroke={lineColor ?? FLAT_COLOR}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                fill: lineColor ?? FLAT_COLOR,
                stroke: "var(--tl-surface)",
              }}
              isAnimationActive
              animationDuration={900}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface CandleShapeProps {
  x?: number;
  width?: number;
  height?: number;
  y?: number;
  o?: number | null;
  h?: number | null;
  l?: number | null;
  v?: number | null;
  candleDomain?: number;
}

/**
 * Custom Recharts bar shape that draws a candlestick (wick + body) from the
 * point's OHLC.
 *
 * Recharts 3.x does not pass an axis scale to custom shape functions. Instead
 * it forwards the pre-computed pixel geometry of the `v` (close) bar and the
 * full data row, so we rebuild the Y scale from the close bar's top edge and
 * height (the bar is anchored at the Y-domain lower bound we inject via
 * `candleDomain`).
 */
function CandleShape({
  x = 0,
  width = 0,
  y = 0,
  height = 0,
  o,
  h,
  l,
  v,
  candleDomain,
}: CandleShapeProps) {
  if (
    typeof o !== "number" ||
    typeof h !== "number" ||
    typeof l !== "number" ||
    !Number.isFinite(v) ||
    !Number.isFinite(candleDomain) ||
    !Number.isFinite(height) ||
    height <= 0 ||
    !(v as number) ||
    !Number.isFinite(v as number) ||
    (v as number) === candleDomain
  ) {
    return null;
  }

  const close = v as number;
  const closeY = y;
  const pixelsPerUnit = height / (close - candleDomain as number);
  const yFor = (price: number) => closeY - (price - close) * pixelsPerUnit;

  const centerX = x + width / 2;
  const wickTop = yFor(h);
  const wickBottom = yFor(l);
  const bodyTop = yFor(Math.max(o, close));
  const bodyBottom = yFor(Math.min(o, close));
  const bodyHeight = Math.max(1, Math.abs(bodyBottom - bodyTop));

  const color = close > o ? UP_COLOR : close < o ? DOWN_COLOR : FLAT_COLOR;
  const halfWidth = Math.max(2, Math.min(6, width / 2 - 0.5));

  return (
    <g>
      <line
        x1={centerX}
        x2={centerX}
        y1={wickTop}
        y2={wickBottom}
        stroke={color}
        strokeWidth={1}
      />
      <rect
        x={centerX - halfWidth}
        y={bodyTop}
        width={halfWidth * 2}
        height={bodyHeight}
        fill={color}
        stroke={color}
      />
    </g>
  );
}

interface ChartLegendItem {
  label: string;
  color: string;
  dashed?: boolean;
}

/**
 * Compact in-chart legend so overlay identity does not rely on colour alone.
 * Shows the bar interval and only the EMAs actually rendered (i.e. those with
 * enough observations to be meaningful), plus support/resistance when present.
 */
function ChartLegend({
  intervalLabel,
  items,
}: {
  intervalLabel: string;
  items: ChartLegendItem[];
}) {
  if (!intervalLabel && items.length === 0) {
    return null;
  }
  return (
    <div
      className="pointer-events-none absolute right-2 top-0.5 z-10 flex flex-wrap items-center justify-end gap-x-3 gap-y-0.5 font-mono text-[10px] leading-none"
      style={{ color: "var(--tl-text-muted)" }}
    >
      <span>{intervalLabel}</span>
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1">
          <span
            className="inline-block h-[2px] w-3"
            style={
              item.dashed
                ? {
                    borderTop: `1px dashed ${item.color}`,
                    background: "transparent",
                  }
                : { background: item.color }
            }
          />
          <span style={{ color: item.color }}>{item.label}</span>
        </span>
      ))}
    </div>
  );
}

function ChartTooltip({ active, payload, timeframe, periods }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload;
  if (!point) return null;

  const rows: Array<[string, string]> = [];

  const hasOHLC =
    typeof point.o === "number" &&
    typeof point.h === "number" &&
    typeof point.l === "number";

  if (hasOHLC) {
    rows.push(["Open", formatPrice(point.o as number)]);
    rows.push(["High", formatPrice(point.h as number)]);
    rows.push(["Low", formatPrice(point.l as number)]);
    rows.push(["Close", formatPrice(point.v)]);
    rows.push(["Volume", formatVolume(point.vol)]);
  } else {
    rows.push(["Price", formatPrice(point.v)]);
  }

  for (const period of periods) {
    const key = `ema${period}` as "ema20" | "ema50" | "ema200";
    rows.push([`EMA${period}`, formatEma(point[key])]);
  }

  return (
    <div
      style={{
        background: "var(--tl-surface)",
        border: "1px solid var(--tl-border)",
        borderRadius: 4,
        fontFamily: "JetBrains Mono",
        fontSize: 12,
        color: "var(--tl-text)",
      }}
    >
      <div style={{ color: "var(--tl-text-muted)", marginBottom: 4 }}>
        {formatChartTooltipLabel(timeframe, point.t)}
      </div>
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-3">
          <span style={{ color: "var(--tl-text-muted)" }}>{label}</span>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
}

function formatPrice(value: number): string {
  return Number.isFinite(value) ? `₹${value.toLocaleString("en-IN")}` : "—";
}

function formatEma(value: number | null | undefined): string {
  const v = pickFirst(value);
  return v === null ? "—" : `₹${v.toLocaleString("en-IN")}`;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
