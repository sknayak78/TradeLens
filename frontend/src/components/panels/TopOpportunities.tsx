import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { Stars, ActionPill } from "@/components/panels/AnalysisBadges";
import TrendBadge from "@/components/panels/TrendBadge";
import { useRankings } from "@/hooks/useMarket";
import type { RiskLevel } from "@/types";

interface TopOpportunitiesProps {
  onSelect?: (symbol: string) => void;
  activeSymbol?: string;
}

const RISK_STYLE: Record<RiskLevel, string> = {
  Low: "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25",
  Medium: "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25",
  High: "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25",
};

function ScoreCell({ score }: { score: number }) {
  const color =
    score >= 90
      ? "bg-[#26a69a]"
      : score >= 80
        ? "bg-[#2962ff]"
        : score >= 60
          ? "bg-[#f5a623]"
          : "bg-[#ef5350]";
  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 h-1 rounded-full bg-[#2a2e39] overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-300`}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
      <span className="font-mono tabular-nums text-xs text-white w-8 text-right">
        {score}
      </span>
    </div>
  );
}

export default function TodaysRankings({
  onSelect,
  activeSymbol,
}: TopOpportunitiesProps) {
  const { data: items = [], isLoading, isError, error, refetch } = useRankings();

  return (
    <PanelCard
      title="Today's Opportunities"
      subtitle="Analysis-driven leaderboard"
      testId="card-top-opportunities"
      action={
        !isLoading && !isError && items.length > 0 ? (
          <span className="text-[10px] font-mono tabular-nums text-[#787b86] uppercase tracking-widest">
            {items.length} ranked
          </span>
        ) : null
      }
    >
      {isLoading && <LoadingState testId="opportunities-loading" />}
      {isError && (
        <ErrorState
          message={error?.message ?? "Failed to load rankings."}
          onRetry={() => refetch()}
          testId="opportunities-error"
        />
      )}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState
          title="No ranked stocks right now"
          description="Fresh picks will appear when the scanner has results."
          testId="opportunities-empty"
        />
      )}
      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto -mx-4">
          <table
            className="w-full text-sm whitespace-nowrap"
            data-testid="opportunities-table"
          >
            <thead>
              <tr className="text-[#787b86] text-[10px] uppercase tracking-widest">
                <th className="text-left font-normal px-3 pb-2 w-10">Rank</th>
                <th className="text-left font-normal px-2 pb-2">Stock</th>
                <th className="text-left font-normal px-2 pb-2">Score</th>
                <th className="text-left font-normal px-2 pb-2">Stars</th>
                <th className="text-left font-normal px-2 pb-2">Trend</th>
                <th className="text-left font-normal px-2 pb-2">Setup</th>
                <th className="text-left font-normal px-2 pb-2">Risk</th>
                <th className="text-left font-normal px-3 pb-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => {
                const isActive = activeSymbol === r.symbol;
                return (
                <tr
                  key={r.symbol}
                  data-testid={`opportunity-row-${r.symbol}`}
                  onClick={() => onSelect?.(r.symbol)}
                  className={`tl-row border-t border-[#2a2e39]/60 ${
                    onSelect ? "cursor-pointer" : ""
                  } ${isActive ? "bg-[#2962ff]/8 border-l-2 border-l-[#2962ff]" : ""}`}
                >
                  <td className="px-3 py-2.5">
                    <span className="font-mono tabular-nums text-[11px] text-[#787b86] font-semibold">
                      #{r.rank.toString().padStart(2, "0")}
                    </span>
                  </td>
                  <td className="px-2 py-2.5">
                    <div className="flex flex-col">
                      <span className="text-white font-medium text-sm">
                        {r.symbol}
                      </span>
                      <span className="text-[11px] text-[#787b86] font-mono tabular-nums">
                        ₹{r.price.toLocaleString("en-IN")}{" "}
                        <span
                          className={
                            r.changePct >= 0
                              ? "text-[#26a69a]"
                              : "text-[#ef5350]"
                          }
                        >
                          {r.changePct >= 0 ? "+" : ""}
                          {r.changePct.toFixed(2)}%
                        </span>
                      </span>
                    </div>
                  </td>
                  <td className="px-2 py-2.5">
                    <ScoreCell score={r.strengthScore} />
                  </td>
                  <td className="px-2 py-2.5">
                    <Stars
                      count={r.stars}
                      testId={`ranking-stars-${r.symbol}`}
                    />
                  </td>
                  <td className="px-2 py-2.5">
                    <TrendBadge
                      trend={r.trend}
                      testId={`ranking-trend-${r.symbol}`}
                    />
                  </td>
                  <td className="px-2 py-2.5">
                    <span
                      data-testid={`ranking-setup-${r.symbol}`}
                      className="inline-flex items-center px-1.5 py-0.5 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25"
                    >
                      {r.tradeSetup}
                    </span>
                  </td>
                  <td className="px-2 py-2.5">
                    <span
                      data-testid={`ranking-risk-${r.symbol}`}
                      className={`inline-flex items-center px-1.5 py-0.5 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider ${RISK_STYLE[r.riskLevel]}`}
                    >
                      {r.riskLevel}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <ActionPill
                      action={r.suggestedAction}
                      testId={`ranking-action-${r.symbol}`}
                    />
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PanelCard>
  );
}
