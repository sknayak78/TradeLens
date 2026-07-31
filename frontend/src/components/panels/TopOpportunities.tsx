import PanelCard from "@/components/panels/PanelCard";
import TrendBadge from "@/components/panels/TrendBadge";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { useOpportunities } from "@/hooks/useMarket";

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 85
      ? "bg-[#26a69a]"
      : score >= 70
        ? "bg-[#2962ff]"
        : score >= 55
          ? "bg-[#f5a623]"
          : "bg-[#ef5350]";
  return (
    <div className="flex items-center gap-2 w-full min-w-[90px]">
      <div className="flex-1 h-1 rounded-full bg-[#2a2e39] overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-300`}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
      <span className="font-mono tabular-nums text-xs text-[#d1d4dc] w-6 text-right">
        {score}
      </span>
    </div>
  );
}

export default function TopOpportunities() {
  const { data: items = [], isLoading, isError, error, refetch } = useOpportunities();

  return (
    <PanelCard
      title="Top Opportunities"
      subtitle="Ranked by TradeLens Score"
      testId="card-top-opportunities"
      action={
        !isLoading && !isError && items.length > 0 ? (
          <span className="text-[10px] font-mono tabular-nums text-[#787b86] uppercase tracking-widest">
            {items.length} picks
          </span>
        ) : null
      }
    >
      {isLoading && <LoadingState testId="opportunities-loading" />}
      {isError && (
        <ErrorState
          message={error?.message ?? "Failed to load opportunities."}
          onRetry={() => refetch()}
          testId="opportunities-error"
        />
      )}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState
          title="No opportunities right now"
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
                <th className="text-left font-normal px-4 pb-2">Stock</th>
                <th className="text-left font-normal px-2 pb-2 w-[35%]">
                  Score
                </th>
                <th className="text-left font-normal px-2 pb-2">Trend</th>
                <th className="text-right font-normal px-4 pb-2">Price</th>
              </tr>
            </thead>
            <tbody>
              {items.map((o) => (
                <tr
                  key={o.symbol}
                  data-testid={`opportunity-row-${o.symbol}`}
                  className="tl-row border-t border-[#2a2e39]/60"
                >
                  <td className="px-4 py-2.5">
                    <div className="flex flex-col">
                      <span className="text-white font-medium text-sm">
                        {o.symbol}
                      </span>
                      <span className="text-[11px] text-[#787b86] truncate max-w-[150px]">
                        {o.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-2 py-2.5">
                    <ScoreBar score={o.score} />
                  </td>
                  <td className="px-2 py-2.5">
                    <TrendBadge trend={o.trend} />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="font-mono tabular-nums text-white">
                      ₹{o.price.toLocaleString("en-IN")}
                    </div>
                    <div
                      className={`font-mono tabular-nums text-[11px] ${
                        o.changePct >= 0
                          ? "text-[#26a69a]"
                          : "text-[#ef5350]"
                      }`}
                    >
                      {o.changePct >= 0 ? "+" : ""}
                      {o.changePct.toFixed(2)}%
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PanelCard>
  );
}
