import { useMarketSummary } from "@/hooks/useMarket";

export default function MarketTicker() {
  const { data, isLoading, isError } = useMarketSummary();

  if (isLoading || isError || !data) {
    return (
      <div
        className="h-6 flex items-center px-4 border-b border-[#D9DDE2]/60 bg-[#F6F7F5]/95 text-[9px] uppercase tracking-widest text-[#667085]"
        data-testid="market-ticker"
      >
        {isLoading ? "Loading market data…" : ""}
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-4 px-4 py-1 border-b border-[#D9DDE2]/60 bg-[#F6F7F5]/95 overflow-x-auto"
      data-testid="market-ticker"
    >
      {data.indices.map((idx) => {
        const isUp = idx.changePct >= 0;
        return (
          <div
            key={idx.symbol}
            data-testid={`ticker-${idx.symbol}`}
            className="flex items-center gap-1.5 whitespace-nowrap"
          >
            <span className="text-[9px] uppercase tracking-widest text-[#667085]">
              {idx.name}
            </span>
            <span className="font-mono tabular-nums text-[11px] text-[#667085]">
              {idx.value.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className={`font-mono tabular-nums text-[10px] ${
                isUp ? "text-[#26a69a]/80" : "text-[#ef5350]/80"
              }`}
            >
              {isUp ? "+" : "-"}
              {Math.abs(idx.changePct).toFixed(2)}%
            </span>
          </div>
        );
      })}
      <div className="ml-auto shrink-0 flex items-center gap-1.5 text-[9px] font-mono tabular-nums text-[#667085] uppercase tracking-widest">
        <span
          className={`w-1 h-1 rounded-full ${
            data.status === "open" ? "bg-[#26a69a]/70" : "bg-[#667085]"
          }`}
        />
        {data.status === "open" ? "Open" : "Closed"}
      </div>
    </div>
  );
}
