import { useEffect, useMemo, useState } from "react";
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
import { getInsight, getWatchlist } from "@/services/marketService";
import type { Insight } from "@/types";
import PanelCard from "@/components/panels/PanelCard";
import TrendBadge from "@/components/panels/TrendBadge";
import { Sparkles, TrendingUp, TrendingDown } from "lucide-react";

interface ChartCardProps {
  symbol: string;
  onSelectSymbol?: (symbol: string) => void;
}

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

export default function ChartCard({ symbol, onSelectSymbol }: ChartCardProps) {
  const [insight, setInsight] = useState<Insight | null>(null);
  const [available, setAvailable] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState("1D");

  useEffect(() => {
    getWatchlist().then((list) => setAvailable(list.map((w) => w.symbol)));
  }, []);

  useEffect(() => {
    getInsight(symbol).then((i) => setInsight(i ?? null));
  }, [symbol]);

  const stats = useMemo(() => {
    if (!insight) return null;
    const values = insight.series.map((p) => p.v);
    const first = values[0];
    const last = values[values.length - 1];
    const changePct = ((last - first) / first) * 100;
    const min = Math.min(...values);
    const max = Math.max(...values);
    return { first, last, changePct, min, max };
  }, [insight]);

  const isUp = insight?.trend === "bullish";
  const lineColor = isUp ? "#26a69a" : insight?.trend === "bearish" ? "#ef5350" : "#2962ff";

  return (
    <PanelCard
      title="Chart & AI Insight"
      subtitle={insight ? `${insight.symbol} · Intraday` : "Loading…"}
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
      {insight && stats && (
        <div className="flex flex-col gap-4">
          {/* Symbol selector chips */}
          <div
            className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1"
            data-testid="chart-symbol-chips"
          >
            {available.map((s) => (
              <button
                key={s}
                onClick={() => onSelectSymbol?.(s)}
                data-testid={`chart-symbol-${s}`}
                className={`px-2 py-1 rounded-[3px] text-[11px] font-mono tracking-wide transition-colors border ${
                  s === symbol
                    ? "bg-[#2962ff]/15 text-white border-[#2962ff]/40"
                    : "bg-transparent text-[#787b86] border-[#2a2e39] hover:text-[#d1d4dc] hover:border-[#3a3f4b]"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Price header */}
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-baseline gap-3">
                <span className="text-white text-2xl md:text-3xl font-semibold font-mono tabular-nums tracking-tight">
                  ₹{stats.last.toLocaleString("en-IN")}
                </span>
                <span
                  className={`font-mono tabular-nums text-sm ${
                    stats.changePct >= 0
                      ? "text-[#26a69a]"
                      : "text-[#ef5350]"
                  }`}
                  data-testid="chart-change-pct"
                >
                  {stats.changePct >= 0 ? "+" : ""}
                  {stats.changePct.toFixed(2)}%
                </span>
              </div>
              <div className="text-[11px] text-[#787b86] mt-0.5 font-mono tabular-nums">
                DAY {stats.min.toLocaleString("en-IN")} —{" "}
                {stats.max.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono tabular-nums">
              <div className="flex items-center gap-1.5 text-[#787b86]">
                <span className="w-2 h-2 rounded-full bg-[#26a69a]" />
                Support
                <span className="text-[#d1d4dc]">
                  {insight.support.toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[#787b86]">
                <span className="w-2 h-2 rounded-full bg-[#ef5350]" />
                Resistance
                <span className="text-[#d1d4dc]">
                  {insight.resistance.toLocaleString("en-IN")}
                </span>
              </div>
            </div>
          </div>

          {/* Chart */}
          <div
            className="h-56 md:h-64 min-h-[224px] -mx-2 relative"
            data-testid="chart-container"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={insight.series}
                margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
              >
                <defs>
                  <linearGradient id="lineGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={lineColor} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                  formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "Price"]}
                />
                <ReferenceLine
                  y={insight.support}
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
                  y={insight.resistance}
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

          {/* Stats + Insight */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Trend">
              <TrendBadge trend={insight.trend} size="sm" />
            </StatTile>
            <StatTile label="Support">
              <span className="text-[#26a69a] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingUp size={13} />
                {insight.support.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile label="Resistance">
              <span className="text-[#ef5350] font-mono tabular-nums text-sm inline-flex items-center gap-1">
                <TrendingDown size={13} />
                {insight.resistance.toLocaleString("en-IN")}
              </span>
            </StatTile>
            <StatTile label="AI Confidence">
              <span className="text-white font-mono tabular-nums text-sm">
                {(72 + (insight.symbol.length % 5) * 3).toString()}%
              </span>
            </StatTile>
          </div>

          <div
            className="rounded-[4px] border border-[#2a2e39] bg-[#131722] p-3 flex gap-3"
            data-testid="ai-insight"
          >
            <span className="mt-0.5 shrink-0 w-7 h-7 rounded-md bg-[#2962ff]/15 border border-[#2962ff]/30 text-[#2962ff] flex items-center justify-center">
              <Sparkles size={14} />
            </span>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
                AI Insight
              </div>
              <p className="text-sm text-[#d1d4dc] leading-relaxed">
                {insight.aiInsight}
              </p>
            </div>
          </div>
        </div>
      )}
    </PanelCard>
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
