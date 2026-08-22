import { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { useStock } from "@/hooks/useMarket";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useAppSettings } from "@/context/SettingsContext";
import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import AnalysisBadges, { Stars, ActionPill } from "@/components/panels/AnalysisBadges";
import RecommendationCard from "@/components/panels/RecommendationCard";
import LearnWhyPanel from "@/components/panels/LearnWhyPanel";
import StockHero from "@/components/panels/StockHero";
import { Sparkles, TrendingUp, TrendingDown } from "lucide-react";
import MetricHelp from "@/components/common/MetricHelp";
import { formatChartTooltipLabel } from "@/lib/chartAxisFormat";
import {
  buildChartTimeAxisPlan,
  formatChartXAxisTickLabel,
  type ChartTimeframe,
} from "@/lib/chartTimeAxis";

interface ChartCardProps {
  symbol: string;
  onSelectSymbol?: (symbol: string) => void;
}

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

export default function ChartCard({ symbol, onSelectSymbol }: ChartCardProps) {
  const { data: watchlist = [] } = useWatchlist();
  const { settings } = useAppSettings();
  const defaultTimeframe = settings?.preferred_timeframe ?? "1W";
  const [timeframe, setTimeframe] = useState(defaultTimeframe);
  const { data: stock, isLoading, isError, error, refetch, isFetching } = useStock(
    symbol,
    timeframe,
  );

  useEffect(() => {
    setTimeframe(defaultTimeframe);
  }, [defaultTimeframe, symbol]);

  const chips = useMemo(() => {
    const watchlistSymbols = watchlist.map((w) => w.symbol);
    if (!symbol || watchlistSymbols.includes(symbol)) {
      return watchlistSymbols;
    }
    return [symbol, ...watchlistSymbols];
  }, [watchlist, symbol]);

  const stats = useMemo(() => {
    if (!stock) return null;
    const values = stock.series.map((p) => p.v);
    if (!values.length) return null;
    const first = values[0];
    const last = values[values.length - 1];
    const changePct = ((last - first) / first) * 100;
    const min = Math.min(...values);
    const max = Math.max(...values);
    return { first, last, changePct, min, max };
  }, [stock]);

  const activeTimeframe = stock?.timeframe ?? timeframe;
  const isUp = stock?.trend === "bullish";
  const lineColor = isUp
    ? "#26a69a"
    : stock?.trend === "bearish"
      ? "#ef5350"
      : "#2962ff";

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartWidthPx, setChartWidthPx] = useState(600);

  useEffect(() => {
    const node = chartContainerRef.current;
    if (!node) return undefined;

    const updateWidth = () => {
      const width = node.getBoundingClientRect().width;
      if (width > 0) {
        setChartWidthPx(width);
      }
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(node);
    return () => observer.disconnect();
  }, [stock?.series]);

  const chartAxisPlan = useMemo(() => {
    if (!stock?.series?.length) return null;
    return buildChartTimeAxisPlan(
      activeTimeframe as ChartTimeframe,
      stock.series,
      chartWidthPx,
    );
  }, [activeTimeframe, chartWidthPx, stock?.series]);

  return (
    <PanelCard
      title="Recommendation & Chart"
      subtitle={
        stock
          ? `${stock.symbol} · ${stock.timeframeLabel ?? timeframe}${
              stock.timeframeFallback ? " (daily fallback)" : ""
            }`
          : "Loading…"
      }
      testId="card-chart"
      action={
        <div className="flex items-center gap-1" data-testid="chart-timeframes">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              data-testid={`timeframe-${tf}`}
              className={`px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors ${
                tf === timeframe
                  ? "bg-[#2962ff]/10 text-[#2962ff]"
                  : "text-[#667085] hover:bg-[#F0F1EF] hover:text-[#1F2933]"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      }
    >
      {isLoading && <LoadingState testId="chart-loading" label="Loading chart" />}
      {isFetching && !isLoading && stock && (
        <div className="text-[10px] text-[#667085] uppercase tracking-widest">
          Updating chart…
        </div>
      )}
      {isError && !isLoading && (
        <ErrorState
          message={error?.message ?? "Failed to load chart data."}
          onRetry={() => refetch()}
          testId="chart-error"
        />
      )}
      {!isLoading && !isError && !stock && (
        <EmptyState
          title="Select a symbol"
          description="Pick a stock to see its chart and AI insight."
          testId="chart-empty"
        />
      )}
      {!isLoading && !isError && stock && stats && (
        <div className="flex flex-col gap-4">
          {/* Stock → verdict → metadata (hero includes recommendation headline) */}
          <StockHero stock={stock} dayLow={stats.min} dayHigh={stats.max} />

          {/* Primary visual evidence — placed immediately after the Mentor context */}
          <div
            ref={chartContainerRef}
            className="h-52 md:h-60 min-h-[220px] w-full -mx-2 relative"
            data-testid="chart-container"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartAxisPlan?.series ?? stock.series}
                margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
              >
                <CartesianGrid
                  stroke="var(--tl-border)"
                  strokeDasharray="2 4"
                  vertical={false}
                />
                <XAxis
                  dataKey="t"
                  stroke="var(--tl-text-muted)"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={false}
                  ticks={chartAxisPlan?.tickValues}
                  interval={0}
                  tickFormatter={(value) =>
                    formatChartXAxisTickLabel(
                      activeTimeframe as ChartTimeframe,
                      String(value),
                    )
                  }
                />
                <YAxis
                  stroke="var(--tl-text-muted)"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={false}
                  domain={["dataMin - 5", "dataMax + 5"]}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--tl-surface)",
                    border: "1px solid var(--tl-border)",
                    borderRadius: 4,
                    fontFamily: "JetBrains Mono",
                    fontSize: 12,
                    color: "var(--tl-text)",
                  }}
                  labelStyle={{ color: "var(--tl-text-muted)" }}
                  labelFormatter={(value) =>
                    formatChartTooltipLabel(activeTimeframe, String(value))
                  }
                  itemStyle={{ color: "var(--tl-text)" }}
                  formatter={(v: number) => [
                    `₹${v.toLocaleString("en-IN")}`,
                    "Price",
                  ]}
                />
                <ReferenceLine
                  y={stock.support}
                  stroke="#26a69a"
                  strokeDasharray="3 3"
                  strokeOpacity={0.5}
                  label={{
                    value: "S",
                    fill: "#26a69a",
                    fontSize: 10,
                    position: "insideLeft",
                  }}
                />
                <ReferenceLine
                  y={stock.resistance}
                  stroke="#ef5350"
                  strokeDasharray="3 3"
                  strokeOpacity={0.5}
                  label={{
                    value: "R",
                    fill: "#ef5350",
                    fontSize: 10,
                    position: "insideLeft",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={lineColor}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: lineColor, stroke: "var(--tl-surface)" }}
                  isAnimationActive
                  animationDuration={900}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quick symbol switcher */}
          <div
            className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1"
            data-testid="chart-symbol-chips"
          >
            {chips.map((s) => (
              <button
                key={s}
                onClick={() => onSelectSymbol?.(s)}
                data-testid={`chart-symbol-${s}`}
                className={`px-2 py-1 rounded-[3px] text-[11px] font-mono tracking-wide transition-colors border shrink-0 ${
                  s === symbol
                    ? "bg-[#2962ff]/10 text-[#1F2933] border-[#2962ff]/40"
                    : "bg-transparent text-[#667085] border-[#D9DDE2] hover:text-[#1F2933] hover:border-[#C5CAD3]"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {stock.recommendation ? (
            <>
              <LearnWhyPanel
                recommendation={stock.recommendation}
                symbol={stock.symbol}
                marketContext={{
                  price: stock.price,
                  ema20: stock.ema20,
                  rsi: stock.rsi,
                  support: stock.support,
                  resistance: stock.resistance,
                }}
                variant="button"
                toggleLabel="Why This View?"
                testIdPrefix="detail-learn-why"
              />
              <RecommendationCard
                recommendation={stock.recommendation}
                marketContext={{
                  price: stock.price,
                  ema20: stock.ema20,
                  rsi: stock.rsi,
                  support: stock.support,
                  resistance: stock.resistance,
                }}
              />
            </>
          ) : (
            <InsightPanel insight={stock.insight} />
          )}

          {/* Supporting metrics — below progressive disclosure */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Strength Score">
              <div className="flex items-center gap-2">
                <span
                  className="text-[#1F2933] font-mono tabular-nums text-sm font-semibold"
                  data-testid="detail-strength-score"
                >
                  {stock.strengthScore}
                </span>
                <Stars count={stock.stars} testId="detail-stars" />
              </div>
            </StatTile>
            <StatTile
              label="Support"
              help={
                <MetricHelp
                  metric="support"
                  context={{ value: stock.support, price: stock.price }}
                  testId="detail-support-help"
                />
              }
            >
              <span className="text-[#26a69a] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingUp size={13} />
                {stock.support.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile
              label="Resistance"
              help={
                <MetricHelp
                  metric="resistance"
                  context={{
                    value: stock.resistance,
                    price: stock.price,
                  }}
                  testId="detail-resistance-help"
                />
              }
            >
              <span className="text-[#ef5350] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingDown size={13} />
                {stock.resistance.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile label="Suggested Action">
              <ActionPill
                action={stock.suggestedAction}
                testId="detail-suggested-action"
              />
            </StatTile>
          </div>

          {/* Three analysis badges */}
          <div
            className="rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-2 flex items-center justify-between gap-3 flex-wrap"
            data-testid="detail-badges"
          >
            <div className="text-[10px] uppercase tracking-widest text-[#667085]">
              {stock.classification}
            </div>
            <AnalysisBadges
              trend={stock.trend}
              setup={stock.tradeSetup}
              risk={stock.riskLevel}
              testIdPrefix="detail-badge"
            />
          </div>

        </div>
      )}
    </PanelCard>
  );
}

/** Legacy technical insight, kept as the fallback when no recommendation. */
function InsightPanel({ insight }: { insight: string }) {
  return (
    <div
      className="rounded-[4px] border border-[#D9DDE2] bg-white p-3 flex gap-3"
      data-testid="ai-insight"
    >
      <span className="mt-0.5 shrink-0 w-7 h-7 rounded-md bg-[#2962ff]/15 border border-[#2962ff]/30 text-[#2962ff] flex items-center justify-center">
        <Sparkles size={14} />
      </span>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
          Insight
        </div>
        <p
          className="text-sm text-[#1F2933] leading-relaxed"
          data-testid="detail-insight"
        >
          {insight}
        </p>
      </div>
    </div>
  );
}

function StatTile({
  label,
  help,
  children,
}: {
  label: string;
  help?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1 flex items-center gap-1">
        <span>{label}</span>
        {help}
      </div>
      <div>{children}</div>
    </div>
  );
}
