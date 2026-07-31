import PanelCard from "@/components/panels/PanelCard";
import TrendBadge from "@/components/panels/TrendBadge";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { useWatchlist, useRemoveFromWatchlist } from "@/hooks/useWatchlist";
import { X } from "lucide-react";

interface WatchlistPanelProps {
  onSelect?: (symbol: string) => void;
  activeSymbol?: string;
  showRemove?: boolean;
}

export default function WatchlistPanel({
  onSelect,
  activeSymbol,
  showRemove = false,
}: WatchlistPanelProps) {
  const { data: items = [], isLoading, isError, error, refetch } = useWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  return (
    <PanelCard
      title="Watchlist"
      subtitle={
        !isLoading && !isError ? `${items.length} instruments tracked` : undefined
      }
      testId="card-watchlist"
      action={
        !isLoading && !isError ? (
          <span className="text-[10px] font-mono tabular-nums text-[#787b86] uppercase tracking-widest">
            Live · Mock
          </span>
        ) : null
      }
    >
      {isLoading && <LoadingState testId="watchlist-loading" />}
      {isError && (
        <ErrorState
          message={error?.message ?? "Failed to load watchlist."}
          onRetry={() => refetch()}
          testId="watchlist-error"
        />
      )}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState
          title="Watchlist is empty"
          description="Add symbols from search to start tracking them here."
          testId="watchlist-empty"
        />
      )}
      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto -mx-4">
          <table
            className="w-full text-sm whitespace-nowrap"
            data-testid="watchlist-table"
          >
            <thead>
              <tr className="text-[#787b86] text-[10px] uppercase tracking-widest">
                <th className="text-left font-normal px-4 pb-2">Stock</th>
                <th className="text-right font-normal px-2 pb-2">Price</th>
                <th className="text-right font-normal px-2 pb-2">RSI</th>
                <th className="text-right font-normal px-2 pb-2">EMA20</th>
                <th className="text-right font-normal px-2 pb-2">VWAP</th>
                <th className="text-right font-normal px-2 pb-2">Score</th>
                <th className="text-left font-normal px-4 pb-2">Trend</th>
                {showRemove && <th className="px-2 pb-2 w-8"></th>}
              </tr>
            </thead>
            <tbody>
              {items.map((w) => {
                const isActive = activeSymbol === w.symbol;
                const rsiColor =
                  w.rsi >= 70
                    ? "text-[#ef5350]"
                    : w.rsi <= 30
                      ? "text-[#26a69a]"
                      : "text-[#d1d4dc]";
                return (
                  <tr
                    key={w.symbol}
                    data-testid={`watchlist-row-${w.symbol}`}
                    onClick={() => onSelect?.(w.symbol)}
                    className={`tl-row border-t border-[#2a2e39]/60 ${
                      onSelect ? "cursor-pointer" : ""
                    } ${
                      isActive
                        ? "bg-[#2962ff]/8 border-l-2 border-l-[#2962ff]"
                        : ""
                    }`}
                  >
                    <td className="px-4 py-2.5">
                      <div className="text-white font-medium text-sm">
                        {w.symbol}
                      </div>
                      <div className="text-[11px] text-[#787b86] truncate max-w-[140px]">
                        {w.name}
                      </div>
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <div className="font-mono tabular-nums text-white">
                        ₹{w.price.toLocaleString("en-IN")}
                      </div>
                      <div
                        className={`font-mono tabular-nums text-[11px] ${
                          w.changePct >= 0
                            ? "text-[#26a69a]"
                            : "text-[#ef5350]"
                        }`}
                      >
                        {w.changePct >= 0 ? "+" : ""}
                        {w.changePct.toFixed(2)}%
                      </div>
                    </td>
                    <td
                      className={`px-2 py-2.5 text-right font-mono tabular-nums ${rsiColor}`}
                    >
                      {w.rsi.toFixed(1)}
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                      {w.ema20.toLocaleString("en-IN")}
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                      {w.vwap.toLocaleString("en-IN")}
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums font-semibold text-white">
                      {w.score}
                    </td>
                    <td className="px-4 py-2.5">
                      <TrendBadge trend={w.trend} />
                    </td>
                    {showRemove && (
                      <td className="px-2 py-2.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeMutation.mutate(w.symbol);
                          }}
                          data-testid={`watchlist-remove-${w.symbol}`}
                          className="p-1 rounded-md text-[#787b86] hover:text-[#ef5350] hover:bg-[#ef5350]/10 transition-colors"
                          aria-label={`Remove ${w.symbol}`}
                        >
                          <X size={14} />
                        </button>
                      </td>
                    )}
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
