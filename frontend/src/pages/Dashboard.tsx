import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import TopOpportunities from "@/components/panels/TopOpportunities";
import WatchlistPanel from "@/components/panels/WatchlistPanel";
import ChartCard from "@/components/panels/ChartCard";
import MarketTicker from "@/components/panels/MarketTicker";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const symbolFromUrl = searchParams.get("symbol")?.trim().toUpperCase() ?? "";
  const [activeSymbol, setActiveSymbol] = useState(symbolFromUrl || "RELIANCE");

  useEffect(() => {
    if (symbolFromUrl) {
      setActiveSymbol(symbolFromUrl);
    }
  }, [symbolFromUrl]);

  const handleSelectSymbol = (symbol: string) => {
    setActiveSymbol(symbol);
    setSearchParams({ symbol }, { replace: true });
  };

  return (
    <div data-testid="dashboard-page" className="min-h-full">
      <MarketTicker />

      <div className="px-4 md:px-6 pt-5 pb-2 flex items-end justify-between flex-wrap gap-2">
        <div className="max-w-3xl">
          <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-[#787b86] mt-1">
            Study curated opportunities, inspect evidence, and learn how the Mentor reads the market.
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

      <div className="px-4 md:px-6 pb-3">
        <EducationalDisclaimer />
      </div>

      <div className="p-4 md:p-6 pt-0 flex flex-col gap-4 max-w-[1600px] mx-auto w-full">
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(320px,38%)_minmax(0,1fr)] gap-4 items-start">
          <div className="flex flex-col gap-4 min-w-0">
            <TopOpportunities
              onSelect={handleSelectSymbol}
              activeSymbol={activeSymbol}
            />
            <WatchlistPanel
              onSelect={handleSelectSymbol}
              activeSymbol={activeSymbol}
            />
          </div>

          <div className="min-w-0">
            <ChartCard
              symbol={activeSymbol}
              onSelectSymbol={handleSelectSymbol}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
