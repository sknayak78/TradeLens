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

  const scrollToOpportunities = () => {
    document
      .getElementById("learning-opportunities")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div data-testid="dashboard-page" className="min-h-full">
      <MarketTicker />

      <div className="px-4 md:px-6 pt-5 pb-2 flex items-end justify-between flex-wrap gap-2">
        <div className="max-w-3xl">
          <h1 className="text-[#1F2933] text-xl md:text-2xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-[#667085] mt-1">
            Study curated opportunities, inspect evidence, and learn how the Mentor reads the market.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono tabular-nums text-[#667085]">
          <span className="px-2 py-1 rounded-[3px] bg-[#F0F1EF] border border-[#D9DDE2] uppercase tracking-widest">
            NSE · India
          </span>
          <span className="px-2 py-1 rounded-[3px] bg-[#F0F1EF] border border-[#D9DDE2] uppercase tracking-widest">
            {new Date().toLocaleDateString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </span>
        </div>
      </div>

      <div className="px-4 md:px-6 pb-3 space-y-3">
        <EducationalDisclaimer />
        <button
          type="button"
          onClick={scrollToOpportunities}
          data-testid="explore-opportunities-cta"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-[#2962ff]/30 bg-[#2962ff]/8 text-[#2962ff] text-sm font-medium hover:bg-[#2962ff]/15 hover:border-[#2962ff]/50 transition-colors"
        >
          <span aria-hidden>↓</span>
          Explore Today&apos;s Learning Opportunities
        </button>
      </div>

      <div className="p-4 md:p-6 pt-0 flex flex-col gap-4 max-w-[1600px] mx-auto w-full">
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(300px,34%)] gap-4 items-start">
          <div className="min-w-0 order-1">
            <ChartCard
              symbol={activeSymbol}
              onSelectSymbol={handleSelectSymbol}
            />
          </div>

          <div className="flex flex-col gap-4 min-w-0 order-2">
            <TopOpportunities
              onSelect={handleSelectSymbol}
              activeSymbol={activeSymbol}
            />
            <WatchlistPanel
              onSelect={handleSelectSymbol}
              activeSymbol={activeSymbol}
              showRemove
            />
          </div>
        </div>
      </div>
    </div>
  );
}
