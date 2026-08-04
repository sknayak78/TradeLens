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

      <div className="p-4 md:p-6 pt-3 flex flex-col gap-4">
        <div className="flex flex-col xl:flex-row gap-4 xl:items-stretch">
          <div className="w-full xl:w-[35%] flex flex-col gap-4">
            <TopOpportunities
              onSelect={setActiveSymbol}
              activeSymbol={activeSymbol}
            />
            <WatchlistPanel
              onSelect={setActiveSymbol}
              activeSymbol={activeSymbol}
            />
            <TodaysFocus />
          </div>

          <div className="w-full xl:w-[65%] flex flex-col gap-4">
            <div className="flex-1 min-h-[420px]">
              <ChartCard
                symbol={activeSymbol}
                onSelectSymbol={setActiveSymbol}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
