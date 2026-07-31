import { useMemo, useState } from "react";
import { NotebookPen, Plus, Trash2 } from "lucide-react";
import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import NewTradeDialog from "@/components/panels/NewTradeDialog";
import { useTrades, useDeleteTrade } from "@/hooks/useTrades";
import type { Trade } from "@/services/tradeService";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function TradingJournal() {
  const { data: trades = [], isLoading, isError, error, refetch } = useTrades();
  const deleteTrade = useDeleteTrade();
  const [dialogOpen, setDialogOpen] = useState(false);

  const stats = useMemo(() => {
    if (!trades.length) return { totalPnl: 0, wins: 0, winRate: 0 };
    const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);
    const wins = trades.filter((t) => t.pnl > 0).length;
    const winRate = (wins / trades.length) * 100;
    return { totalPnl, wins, winRate };
  }, [trades]);

  return (
    <div data-testid="journal-page" className="p-4 md:p-6">
      <div className="mb-4 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
            Trading Journal
          </h1>
          <p className="text-xs text-[#787b86] mt-1">
            Log every trade. Review with brutal honesty.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-white text-sm font-medium transition-colors"
          onClick={() => setDialogOpen(true)}
          data-testid="journal-new-trade"
        >
          <Plus size={14} />
          New Trade
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <StatCard
          label="Net P&L"
          value={`₹${stats.totalPnl.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          positive={stats.totalPnl >= 0}
          testId="journal-stat-pnl"
        />
        <StatCard
          label="Win Rate"
          value={`${stats.winRate.toFixed(0)}%`}
          positive={stats.winRate >= 50}
          testId="journal-stat-winrate"
        />
        <StatCard
          label="Total Trades"
          value={`${trades.length}`}
          positive
          testId="journal-stat-total"
        />
      </div>

      <PanelCard
        title="Recent Trades"
        subtitle="Chronological log"
        testId="journal-trades"
      >
        {isLoading && <LoadingState testId="journal-loading" />}
        {isError && (
          <ErrorState
            message={error?.message ?? "Failed to load trades."}
            onRetry={() => refetch()}
            testId="journal-error"
          />
        )}
        {!isLoading && !isError && trades.length === 0 && (
          <EmptyState
            title="No trades logged yet"
            description="Tap 'New Trade' to record your first entry."
            testId="journal-empty"
          />
        )}
        {!isLoading && !isError && trades.length > 0 && (
          <div className="overflow-x-auto -mx-4">
            <table className="w-full text-sm whitespace-nowrap">
              <thead>
                <tr className="text-[#787b86] text-[10px] uppercase tracking-widest">
                  <th className="text-left font-normal px-4 pb-2">ID</th>
                  <th className="text-left font-normal px-2 pb-2">Date</th>
                  <th className="text-left font-normal px-2 pb-2">Stock</th>
                  <th className="text-left font-normal px-2 pb-2">Side</th>
                  <th className="text-right font-normal px-2 pb-2">Entry</th>
                  <th className="text-right font-normal px-2 pb-2">Exit</th>
                  <th className="text-right font-normal px-2 pb-2">Qty</th>
                  <th className="text-right font-normal px-2 pb-2">P&amp;L</th>
                  <th className="text-left font-normal px-4 pb-2">Note</th>
                  <th className="pb-2 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t: Trade) => (
                  <tr
                    key={t.id}
                    data-testid={`journal-row-${t.id}`}
                    className="tl-row border-t border-[#2a2e39]/60"
                  >
                    <td className="px-4 py-2.5 font-mono tabular-nums text-[#787b86] text-xs">
                      T-{t.id.toString().padStart(4, "0")}
                    </td>
                    <td className="px-2 py-2.5 text-[#d1d4dc]">
                      {formatDate(t.trade_date)}
                    </td>
                    <td className="px-2 py-2.5 text-white font-medium">
                      {t.symbol}
                    </td>
                    <td className="px-2 py-2.5">
                      <span
                        className={`px-1.5 py-0.5 rounded-[3px] text-[10px] font-mono border ${
                          t.side === "LONG"
                            ? "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25"
                            : "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25"
                        }`}
                      >
                        {t.side}
                      </span>
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                      {t.entry_price.toLocaleString("en-IN")}
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                      {t.exit_price.toLocaleString("en-IN")}
                    </td>
                    <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                      {t.quantity}
                    </td>
                    <td
                      className={`px-2 py-2.5 text-right font-mono tabular-nums font-semibold ${
                        t.pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                      }`}
                    >
                      {t.pnl >= 0 ? "+" : ""}
                      ₹
                      {Math.abs(t.pnl).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-4 py-2.5 text-[#787b86] text-xs max-w-[240px] truncate">
                      {t.notes || "—"}
                    </td>
                    <td className="px-2 py-2.5">
                      <button
                        onClick={() => deleteTrade.mutate(t.id)}
                        data-testid={`journal-delete-${t.id}`}
                        className="p-1 rounded-md text-[#787b86] hover:text-[#ef5350] hover:bg-[#ef5350]/10 transition-colors"
                        aria-label={`Delete trade ${t.id}`}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 rounded-[4px] border border-dashed border-[#2a2e39] bg-[#131722] p-4 flex items-center gap-3">
          <NotebookPen size={18} className="text-[#787b86]" />
          <p className="text-xs text-[#787b86]">
            Trades are stored in your local SQLite database. Add, edit or
            delete entries — they persist across refreshes.
          </p>
        </div>
      </PanelCard>

      <NewTradeDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
}

function StatCard({
  label,
  value,
  positive,
  testId,
}: {
  label: string;
  value: string;
  positive: boolean;
  testId?: string;
}) {
  return (
    <div
      className="rounded-[4px] border border-[#2a2e39] bg-[#1e222d] p-4"
      data-testid={testId}
    >
      <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
        {label}
      </div>
      <div
        className={`font-mono tabular-nums text-2xl font-semibold ${
          positive ? "text-[#26a69a]" : "text-[#ef5350]"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
