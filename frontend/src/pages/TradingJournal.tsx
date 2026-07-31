import { NotebookPen, Plus } from "lucide-react";
import PanelCard from "@/components/panels/PanelCard";

const SAMPLE_TRADES = [
  {
    id: "T-0142",
    date: "12 Feb 2026",
    symbol: "RELIANCE",
    side: "LONG",
    entry: 2905.4,
    exit: 2934.55,
    qty: 25,
    pnl: 728.75,
    note: "Cup & handle setup, respected VWAP support",
  },
  {
    id: "T-0141",
    date: "11 Feb 2026",
    symbol: "TATAMOTORS",
    side: "LONG",
    entry: 948.6,
    exit: 972.65,
    qty: 40,
    pnl: 962.0,
    note: "Momentum breakout with volume expansion",
  },
  {
    id: "T-0140",
    date: "10 Feb 2026",
    symbol: "ASIANPAINT",
    side: "SHORT",
    entry: 2870.2,
    exit: 2842.15,
    qty: 15,
    pnl: 420.75,
    note: "20-EMA rejection, RSI weakness",
  },
  {
    id: "T-0139",
    date: "09 Feb 2026",
    symbol: "SBIN",
    side: "LONG",
    entry: 828.5,
    exit: 812.4,
    qty: 60,
    pnl: -966.0,
    note: "Failed breakout — stopped out on volume",
  },
];

export default function TradingJournal() {
  const totalPnl = SAMPLE_TRADES.reduce((s, t) => s + t.pnl, 0);
  const wins = SAMPLE_TRADES.filter((t) => t.pnl > 0).length;
  const winRate = (wins / SAMPLE_TRADES.length) * 100;

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
          data-testid="journal-new-trade"
        >
          <Plus size={14} />
          New Trade
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <StatCard
          label="Net P&L"
          value={`₹${totalPnl.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          positive={totalPnl >= 0}
          testId="journal-stat-pnl"
        />
        <StatCard
          label="Win Rate"
          value={`${winRate.toFixed(0)}%`}
          positive={winRate >= 50}
          testId="journal-stat-winrate"
        />
        <StatCard
          label="Total Trades"
          value={`${SAMPLE_TRADES.length}`}
          positive
          testId="journal-stat-total"
        />
      </div>

      <PanelCard
        title="Recent Trades"
        subtitle="Chronological log"
        testId="journal-trades"
      >
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
              </tr>
            </thead>
            <tbody>
              {SAMPLE_TRADES.map((t) => (
                <tr
                  key={t.id}
                  data-testid={`journal-row-${t.id}`}
                  className="tl-row border-t border-[#2a2e39]/60"
                >
                  <td className="px-4 py-2.5 font-mono tabular-nums text-[#787b86] text-xs">
                    {t.id}
                  </td>
                  <td className="px-2 py-2.5 text-[#d1d4dc]">{t.date}</td>
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
                    {t.entry.toLocaleString("en-IN")}
                  </td>
                  <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                    {t.exit.toLocaleString("en-IN")}
                  </td>
                  <td className="px-2 py-2.5 text-right font-mono tabular-nums text-[#d1d4dc]">
                    {t.qty}
                  </td>
                  <td
                    className={`px-2 py-2.5 text-right font-mono tabular-nums font-semibold ${
                      t.pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                    }`}
                  >
                    {t.pnl >= 0 ? "+" : ""}
                    ₹{Math.abs(t.pnl).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-2.5 text-[#787b86] text-xs max-w-[240px] truncate">
                    {t.note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 rounded-[4px] border border-dashed border-[#2a2e39] bg-[#131722] p-4 flex items-center gap-3">
          <NotebookPen size={18} className="text-[#787b86]" />
          <p className="text-xs text-[#787b86]">
            Journaling is mocked — trade logs are static samples. Live logging
            will connect to your broker in a future release.
          </p>
        </div>
      </PanelCard>
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
