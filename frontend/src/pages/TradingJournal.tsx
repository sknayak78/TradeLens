import { Fragment, useMemo, useState } from "react";
import { NotebookPen, Plus, Trash2 } from "lucide-react";
import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import NewTradeDialog from "@/components/panels/NewTradeDialog";
import TradeMentorSnapshotPanel from "@/components/panels/TradeMentorSnapshotPanel";
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

function formatMoney(value: number): string {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}₹${Math.abs(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function TradingJournal() {
  const { data: trades = [], isLoading, isError, error, refetch } = useTrades();
  const deleteTrade = useDeleteTrade();
  const [dialogOpen, setDialogOpen] = useState(false);

  const stats = useMemo(() => {
    const closed = trades.filter((trade) => trade.status === "CLOSED");
    const open = trades.filter((trade) => trade.status === "OPEN");
    const realizedPnl = closed.reduce((sum, trade) => sum + trade.pnl, 0);
    const unrealizedPnl = open.reduce(
      (sum, trade) => sum + (trade.unrealized_pnl ?? 0),
      0,
    );
    const wins = closed.filter((trade) => trade.pnl > 0).length;
    const winRate = closed.length ? (wins / closed.length) * 100 : 0;
    return {
      realizedPnl,
      unrealizedPnl,
      wins,
      winRate,
      closedCount: closed.length,
      openCount: open.length,
      totalCount: trades.length,
    };
  }, [trades]);

  return (
    <div data-testid="journal-page" className="p-4 md:p-6">
      <div className="mb-4 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[#1F2933] text-xl md:text-2xl font-semibold tracking-tight">
            Trading Journal
          </h1>
          <p className="text-xs text-[#667085] mt-1">
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

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <StatCard
          label="Realized P&L"
          value={formatMoney(stats.realizedPnl)}
          positive={stats.realizedPnl >= 0}
          testId="journal-stat-realized-pnl"
        />
        <StatCard
          label="Unrealized P&L"
          value={formatMoney(stats.unrealizedPnl)}
          positive={stats.unrealizedPnl >= 0}
          testId="journal-stat-unrealized-pnl"
        />
        <StatCard
          label="Win Rate (Closed)"
          value={`${stats.winRate.toFixed(0)}%`}
          positive={stats.winRate >= 50}
          testId="journal-stat-winrate"
        />
        <StatCard
          label="Open / Closed"
          value={`${stats.openCount} / ${stats.closedCount}`}
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
                <tr className="text-[#667085] text-[10px] uppercase tracking-widest">
                  <th className="text-left font-normal px-4 pb-2">ID</th>
                  <th className="text-left font-normal px-2 pb-2">Entry</th>
                  <th className="text-left font-normal px-2 pb-2">Exit</th>
                  <th className="text-left font-normal px-2 pb-2">Stock</th>
                  <th className="text-left font-normal px-2 pb-2">Side</th>
                  <th className="text-left font-normal px-2 pb-2">Status</th>
                  <th className="text-right font-normal px-2 pb-2">Entry</th>
                  <th className="text-right font-normal px-2 pb-2">Exit</th>
                  <th className="text-right font-normal px-2 pb-2">Qty</th>
                  <th className="text-right font-normal px-2 pb-2">P&amp;L</th>
                  <th className="text-left font-normal px-4 pb-2">Note</th>
                  <th className="pb-2 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade: Trade) => {
                  const isOpen = trade.status === "OPEN";
                  const pnlValue = isOpen
                    ? trade.unrealized_pnl ?? 0
                    : trade.pnl;
                  return (
                    <Fragment key={trade.id}>
                      <tr
                        data-testid={`journal-row-${trade.id}`}
                        className="tl-row border-t border-[#D9DDE2]/60"
                      >
                      <td className="px-4 py-2.5 font-mono tabular-nums text-[#667085] text-xs">
                        T-{trade.id.toString().padStart(4, "0")}
                      </td>
                      <td className="px-2 py-2.5 text-[#1F2933]">
                        {formatDate(trade.trade_date)}
                      </td>
                      <td className="px-2 py-2.5 text-[#1F2933]">
                        {trade.exit_date ? formatDate(trade.exit_date) : "—"}
                      </td>
                      <td className="px-2 py-2.5 text-[#1F2933] font-medium">
                        {trade.symbol}
                      </td>
                      <td className="px-2 py-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded-[3px] text-[10px] font-mono border ${
                            trade.side === "LONG"
                              ? "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25"
                              : "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25"
                          }`}
                        >
                          {trade.side}
                        </span>
                      </td>
                      <td className="px-2 py-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded-[3px] text-[10px] font-mono border ${
                            isOpen
                              ? "text-[#2962ff] bg-[#2962ff]/10 border-[#2962ff]/25"
                              : "text-[#667085] bg-[#F0F1EF] border-[#D9DDE2]"
                          }`}
                        >
                          {trade.status}
                        </span>
                      </td>
                      <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#1F2933]">
                        {trade.entry_price.toLocaleString("en-IN")}
                      </td>
                      <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#1F2933]">
                        {isOpen
                          ? trade.current_price?.toLocaleString("en-IN") ?? "—"
                          : trade.exit_price?.toLocaleString("en-IN") ?? "—"}
                      </td>
                      <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#1F2933]">
                        {trade.quantity}
                      </td>
                      <td
                        className={`px-2 py-2.5 text-right font-mono tabular-nums font-semibold ${
                          pnlValue >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                        }`}
                      >
                        {formatMoney(pnlValue)}
                        {isOpen && (
                          <div className="text-[10px] font-normal text-[#667085]">
                            unrealized
                          </div>
                        )}
                        {!isOpen && trade.holding_period_days != null && (
                          <div className="text-[10px] font-normal text-[#667085]">
                            {trade.holding_period_days}d hold
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-[#667085] text-xs max-w-[240px] truncate">
                        {trade.notes || "—"}
                      </td>
                      <td className="px-2 py-2.5">
                        <button
                          onClick={() => deleteTrade.mutate(trade.id)}
                          data-testid={`journal-delete-${trade.id}`}
                          className="p-1 rounded-md text-[#667085] hover:text-[#ef5350] hover:bg-[#ef5350]/10 transition-colors"
                          aria-label={`Delete trade ${trade.id}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                    <tr
                      key={`${trade.id}-details`}
                      className="border-t border-[#D9DDE2]/40 bg-[#FCFCFB]"
                    >
                      <td colSpan={12} className="px-4 py-3">
                        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,280px)]">
                          <TradeMentorSnapshotPanel
                            snapshot={trade.mentor_snapshot}
                            tradeId={trade.id}
                          />
                          <div
                            className="rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-3"
                            data-testid={`journal-note-${trade.id}`}
                          >
                            <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
                              My Note
                            </div>
                            <p className="text-xs text-[#1F2933] leading-relaxed">
                              {trade.notes?.trim()
                                ? trade.notes
                                : "No personal note added."}
                            </p>
                          </div>
                        </div>
                      </td>
                    </tr>
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 rounded-[4px] border border-dashed border-[#D9DDE2] bg-white p-4 flex items-center gap-3">
          <NotebookPen size={18} className="text-[#667085]" />
          <p className="text-xs text-[#667085]">
            Realized P&amp;L reflects closed trades only. Open positions show
            unrealized P&amp;L using the latest market price.
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
      className="rounded-[4px] border border-[#D9DDE2] bg-white p-4"
      data-testid={testId}
    >
      <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
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
