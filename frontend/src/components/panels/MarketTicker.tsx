import { useMarketSummary } from "@/hooks/useMarket";

export default function MarketTicker() {
  const { data, isLoading, isError } = useMarketSummary();

  if (isLoading || isError || !data) {
    return (
      <div
        className="h-10 flex items-center px-4 border-b border-[#2a2e39] bg-[#131722] text-[10px] uppercase tracking-widest text-[#787b86]"
        data-testid="market-ticker"
      >
        {isLoading ? "Loading market data…" : ""}
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-6 px-4 py-2.5 border-b border-[#2a2e39] bg-[#131722] overflow-x-auto"
      data-testid="market-ticker"
    >
      {data.indices.map((idx) => {
        const isUp = idx.changePct >= 0;
        return (
          <div
            key={idx.symbol}
            data-testid={`ticker-${idx.symbol}`}
            className="flex items-center gap-2 whitespace-nowrap"
          >
            <span className="text-[10px] uppercase tracking-widest text-[#787b86] font-semibold">
              {idx.name}
            </span>
            <span className="font-mono tabular-nums text-sm text-white">
              {idx.value.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className={`font-mono tabular-nums text-xs ${
                isUp ? "text-[#26a69a]" : "text-[#ef5350]"
              }`}
            >
              {isUp ? "▲" : "▼"} {Math.abs(idx.changePct).toFixed(2)}%
            </span>
          </div>
        );
      })}
      <div className="ml-auto shrink-0 flex items-center gap-2 text-[10px] font-mono tabular-nums text-[#787b86] uppercase tracking-widest">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            data.status === "open" ? "bg-[#26a69a] tl-pulse" : "bg-[#ef5350]"
          }`}
        />
        Market {data.status === "open" ? "Open" : "Closed"}
      </div>
    </div>
  );
}
