import { useState } from "react";
import TodaysFocus from "@/components/panels/TodaysFocus";
import TopOpportunities from "@/components/panels/TopOpportunities";
import WatchlistPanel from "@/components/panels/WatchlistPanel";
import ChartCard from "@/components/panels/ChartCard";
import MarketTicker from "@/components/panels/MarketTicker";

export default function Dashboard() {
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");

  return (
    <div data-testid="dashboard-page" className="min-h-full">
      <MarketTicker />

      {/* Page title */}
      <div className="px-4 md:px-6 pt-5 pb-2 flex items-end justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-[#787b86] mt-1">
            Real-time market pulse · Powered by TradeLens analytics
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono tabular-nums text-[#787b86]">
          <span className="px-2 py-1 rounded-[3px] bg-[#1e222d] border border-[#2a2e39] uppercase tracking-widest">
            NSE · India
          </span>
          <span className="px-2 py-1 rounded-[3px] bg-[#1e222d] border border-[#2a2e39] uppercase tracking-widest">
            {new Date().toLocaleDateString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </span>
        </div>
      </div>

      <div className="p-4 md:p-6 pt-3 grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 xl:col-span-4">
          <TodaysFocus />
        </div>
        <div className="lg:col-span-7 xl:col-span-8">
          <TopOpportunities onSelect={setActiveSymbol} activeSymbol={activeSymbol} />
        </div>
        <div className="lg:col-span-12 xl:col-span-7">
          <WatchlistPanel
            onSelect={setActiveSymbol}
            activeSymbol={activeSymbol}
          />
        </div>
        <div className="lg:col-span-12 xl:col-span-5">
          <ChartCard
            symbol={activeSymbol}
            onSelectSymbol={setActiveSymbol}
          />
        </div>
      </div>
    </div>
  );
}
