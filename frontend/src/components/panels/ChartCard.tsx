import { useMemo, useState } from "react";
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
import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import AnalysisBadges, { Stars, ActionPill } from "@/components/panels/AnalysisBadges";
import RecommendationCard from "@/components/panels/RecommendationCard";
import StockHero from "@/components/panels/StockHero";
import {
  resolveChartSetup,
  resolveChartSuggestedAction,
} from "@/components/panels/stockDetailAuthority";
import { Sparkles, TrendingUp, TrendingDown } from "lucide-react";

interface ChartCardProps {
  symbol: string;
  onSelectSymbol?: (symbol: string) => void;
}

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

export default function ChartCard({ symbol, onSelectSymbol }: ChartCardProps) {
  const { data: watchlist = [] } = useWatchlist();
  const { data: stock, isLoading, isError, error, refetch } = useStock(symbol);
  const [timeframe, setTimeframe] = useState("1D");

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

  const isUp = stock?.trend === "bullish";
  const lineColor = isUp
    ? "#26a69a"
    : stock?.trend === "bearish"
      ? "#ef5350"
      : "#2962ff";

  return (
    <PanelCard
      title="Recommendation & Chart"
      subtitle={stock ? `${stock.symbol} · Intraday` : "Loading…"}
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
                  ? "bg-[#2962ff]/15 text-[#2962ff]"
                  : "text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      }
    >
      {isLoading && <LoadingState testId="chart-loading" label="Loading chart" />}
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
          {/* Which stock am I looking at? */}
          <StockHero stock={stock} dayLow={stats.min} dayHigh={stats.max} />

          {/* Symbol chips */}
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
                    ? "bg-[#2962ff]/15 text-white border-[#2962ff]/40"
                    : "bg-transparent text-[#787b86] border-[#2a2e39] hover:text-[#d1d4dc] hover:border-[#3a3f4b]"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Recommendation — the primary answer to "should I buy today?".
              Falls back to the legacy insight panel when the engine could not
              produce a decision. */}
          {stock.recommendation ? (
            <RecommendationCard recommendation={stock.recommendation} />
          ) : (
            <InsightPanel insight={stock.insight} />
          )}

          {/* Chart */}
          <div
            className="h-56 md:h-64 min-h-[240px] w-full -mx-2 relative"
            data-testid="chart-container"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={stock.series}
                margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
              >
                <CartesianGrid
                  stroke="#2a2e39"
                  strokeDasharray="2 4"
                  vertical={false}
                />
                <XAxis
                  dataKey="t"
                  stroke="#787b86"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#787b86"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  tickLine={false}
                  axisLine={false}
                  domain={["dataMin - 5", "dataMax + 5"]}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    background: "#131722",
                    border: "1px solid #2a2e39",
                    borderRadius: 4,
                    fontFamily: "JetBrains Mono",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#787b86" }}
                  itemStyle={{ color: "#d1d4dc" }}
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
                  activeDot={{ r: 4, fill: lineColor, stroke: "#131722" }}
                  isAnimationActive
                  animationDuration={900}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Stats + insight */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Strength Score">
              <div className="flex items-center gap-2">
                <span
                  className="text-white font-mono tabular-nums text-sm font-semibold"
                  data-testid="detail-strength-score"
                >
                  {stock.strengthScore}
                </span>
                <Stars count={stock.stars} testId="detail-stars" />
              </div>
            </StatTile>
            <StatTile label="Support">
              <span className="text-[#26a69a] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingUp size={13} />
                {stock.support.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile label="Resistance">
              <span className="text-[#ef5350] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingDown size={13} />
                {stock.resistance.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile label="Suggested Action">
              <ActionPill
                action={resolveChartSuggestedAction(stock)}
                testId="detail-suggested-action"
              />
            </StatTile>
          </div>

          {/* Three analysis badges */}
          <div
            className="rounded-[4px] border border-[#2a2e39] bg-[#131722] px-3 py-2 flex items-center justify-between gap-3 flex-wrap"
            data-testid="detail-badges"
          >
            <div className="text-[10px] uppercase tracking-widest text-[#787b86]">
              {stock.classification}
            </div>
            <AnalysisBadges
              trend={stock.trend}
              setup={resolveChartSetup(stock)}
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
      className="rounded-[4px] border border-[#2a2e39] bg-[#131722] p-3 flex gap-3"
      data-testid="ai-insight"
    >
      <span className="mt-0.5 shrink-0 w-7 h-7 rounded-md bg-[#2962ff]/15 border border-[#2962ff]/30 text-[#2962ff] flex items-center justify-center">
        <Sparkles size={14} />
      </span>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
          Insight
        </div>
        <p
          className="text-sm text-[#d1d4dc] leading-relaxed"
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
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[4px] border border-[#2a2e39] bg-[#131722] px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
        {label}
      </div>
      <div>{children}</div>
    </div>
  );
}
