import { TrendingDown, TrendingUp } from "lucide-react";
import type { StockDetail } from "@/services/marketService";

interface StockHeroProps {
  stock: StockDetail;
  /** Intraday low/high of the rendered series. */
  dayLow: number;
  dayHigh: number;
}

/**
 * "Which stock am I looking at?" — sticks to the top of the panel so the
 * selected instrument stays identifiable while the recommendation scrolls.
 */
export default function StockHero({ stock, dayLow, dayHigh }: StockHeroProps) {
  const up = stock.changePct >= 0;

  return (
    <div
      className="sticky top-0 z-10 -mx-4 px-4 py-3 bg-[#131722]/95 backdrop-blur border-b border-[#2a2e39] flex items-start justify-between gap-4 flex-wrap"
      data-testid="stock-hero"
    >
      <div className="min-w-0">
        <h3
          className="text-white text-lg md:text-xl font-semibold leading-tight truncate"
          data-testid="stock-hero-name"
        >
          {stock.name}
        </h3>
        <div className="flex items-center gap-2 flex-wrap mt-1">
          <span
            className="px-1.5 py-0.5 rounded-[3px] border border-[#2a2e39] bg-[#1a1f2b] text-[10px] font-mono tracking-wider text-[#d1d4dc]"
            data-testid="stock-hero-symbol"
          >
            NSE: {stock.symbol}
          </span>
          {stock.sector && (
            <span
              className="text-[10px] uppercase tracking-widest text-[#787b86]"
              data-testid="stock-hero-sector"
            >
              {stock.sector}
            </span>
          )}
        </div>
      </div>

      <div className="text-right shrink-0">
        <div className="flex items-baseline gap-2 justify-end">
          <span
            className="text-white text-2xl md:text-3xl font-semibold font-mono tabular-nums tracking-tight"
            data-testid="stock-hero-price"
          >
            ₹{stock.price.toLocaleString("en-IN")}
          </span>
          <span
            className={`inline-flex items-center gap-1 font-mono tabular-nums text-sm font-semibold ${
              up ? "text-[#26a69a]" : "text-[#ef5350]"
            }`}
            data-testid="stock-hero-change"
          >
            {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            {up ? "+" : ""}
            {stock.changePct.toFixed(2)}%
          </span>
        </div>
        <div className="text-[10px] text-[#787b86] mt-0.5 font-mono tabular-nums">
          DAY {dayLow.toLocaleString("en-IN")} — {dayHigh.toLocaleString("en-IN")}
          <span className="mx-1.5 text-[#2a2e39]">|</span>
          S {stock.support.toLocaleString("en-IN")}
          <span className="mx-1.5 text-[#2a2e39]">|</span>
          R {stock.resistance.toLocaleString("en-IN")}
        </div>
      </div>
    </div>
  );
}
