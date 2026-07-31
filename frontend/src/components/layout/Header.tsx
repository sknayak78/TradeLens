import { useEffect, useMemo, useRef, useState } from "react";
import { Search, RefreshCw, Settings, Menu, LineChart, Plus, Check } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useWatchlist, useAddToWatchlist } from "@/hooks/useWatchlist";
import { marketService, StockSummary } from "@/services/marketService";

interface HeaderProps {
  onOpenMobileNav: () => void;
}

export default function Header({ onOpenMobileNav }: HeaderProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: watchlist = [] } = useWatchlist();
  const addToWatchlist = useAddToWatchlist();

  const watchlistSet = useMemo(
    () => new Set(watchlist.map((w) => w.symbol)),
    [watchlist],
  );

  useEffect(() => {
    let cancelled = false;
    const q = query.trim();
    if (!q) {
      setResults([]);
      setOpen(false);
      return;
    }
    marketService
      .searchStocks(q, 8)
      .then((r) => {
        if (!cancelled) {
          setResults(r);
          setOpen(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setResults([]);
          setOpen(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [query]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleRefresh = () => {
    setSpinning(true);
    queryClient.invalidateQueries();
    setTimeout(() => {
      setSpinning(false);
      setLastRefresh(new Date());
    }, 700);
  };

  const handleAdd = (symbol: string) => {
    if (watchlistSet.has(symbol)) return;
    addToWatchlist.mutate(symbol);
  };

  return (
    <header
      className="h-14 flex items-center justify-between px-3 md:px-4 border-b border-[#2a2e39] bg-[#131722] sticky top-0 z-30"
      data-testid="app-header"
    >
      <div className="flex items-center gap-2 md:gap-4 min-w-0">
        <button
          className="md:hidden p-2 rounded-md hover:bg-[#2a2e39] text-[#787b86]"
          onClick={onOpenMobileNav}
          data-testid="mobile-nav-toggle"
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>
        <button
          className="flex items-center gap-2 pr-2 md:pr-4 md:border-r md:border-[#2a2e39] shrink-0"
          onClick={() => navigate("/")}
          data-testid="app-logo"
        >
          <span className="w-8 h-8 flex items-center justify-center rounded-md bg-[#2962ff]/15 border border-[#2962ff]/40 text-[#2962ff]">
            <LineChart size={18} strokeWidth={2.5} />
          </span>
          <span className="hidden sm:flex items-baseline gap-1">
            <span className="text-white font-semibold tracking-tight text-base">
              Trade
            </span>
            <span className="text-[#2962ff] font-semibold tracking-tight text-base">
              Lens
            </span>
          </span>
        </button>

        <div
          ref={containerRef}
          className="relative w-full max-w-md"
          data-testid="header-search-wrapper"
        >
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#787b86] pointer-events-none"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query && setOpen(true)}
            placeholder="Search stocks e.g. RELIANCE, TCS…"
            data-testid="stock-search-input"
            className="w-full h-9 pl-9 pr-3 rounded-md bg-[#1e222d] border border-[#2a2e39] text-sm text-[#d1d4dc] placeholder:text-[#787b86] focus:border-[#2962ff]/60 focus:outline-none transition-colors"
          />
          {open && results.length > 0 && (
            <div
              className="absolute left-0 right-0 top-11 rounded-md border border-[#2a2e39] bg-[#1e222d] shadow-2xl overflow-hidden z-40 tl-fade-in"
              data-testid="stock-search-results"
            >
              {results.map((s) => {
                const inWatchlist = watchlistSet.has(s.symbol);
                return (
                  <div
                    key={s.symbol}
                    className="flex items-center justify-between px-3 py-2 hover:bg-[#2a2e39] transition-colors"
                    data-testid={`search-result-${s.symbol}`}
                  >
                    <div className="min-w-0">
                      <div className="text-sm text-white font-medium">
                        {s.symbol}
                      </div>
                      <div className="text-xs text-[#787b86] truncate">
                        {s.name}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right shrink-0">
                        <div className="font-mono tabular-nums text-sm text-[#d1d4dc]">
                          ₹{s.price.toLocaleString("en-IN")}
                        </div>
                        <div
                          className={`font-mono tabular-nums text-xs ${
                            s.changePct >= 0
                              ? "text-[#26a69a]"
                              : "text-[#ef5350]"
                          }`}
                        >
                          {s.changePct >= 0 ? "+" : ""}
                          {s.changePct.toFixed(2)}%
                        </div>
                      </div>
                      <button
                        onClick={() => handleAdd(s.symbol)}
                        disabled={inWatchlist || addToWatchlist.isPending}
                        data-testid={`search-add-${s.symbol}`}
                        className={`p-1.5 rounded-md border transition-colors ${
                          inWatchlist
                            ? "text-[#26a69a] border-[#26a69a]/30 bg-[#26a69a]/10 cursor-default"
                            : "text-[#787b86] border-[#2a2e39] hover:text-[#2962ff] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/10"
                        }`}
                        aria-label={
                          inWatchlist ? "Already in watchlist" : "Add to watchlist"
                        }
                      >
                        {inWatchlist ? <Check size={12} /> : <Plus size={12} />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {open && query && results.length === 0 && (
            <div className="absolute left-0 right-0 top-11 rounded-md border border-[#2a2e39] bg-[#1e222d] px-3 py-2 text-xs text-[#787b86] z-40">
              No matches for “{query}”
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1 md:gap-2 shrink-0">
        <span
          className="hidden md:inline text-[10px] text-[#787b86] font-mono tabular-nums mr-1"
          data-testid="last-refresh-time"
        >
          UPDATED {lastRefresh.toLocaleTimeString("en-IN", { hour12: false })}
        </span>
        <button
          onClick={handleRefresh}
          className="p-2 rounded-md hover:bg-[#2a2e39] text-[#787b86] hover:text-white transition-colors"
          data-testid="refresh-button"
          aria-label="Refresh data"
        >
          <RefreshCw size={16} className={spinning ? "animate-spin" : ""} />
        </button>
        <button
          onClick={() => navigate("/settings")}
          className="p-2 rounded-md hover:bg-[#2a2e39] text-[#787b86] hover:text-white transition-colors"
          data-testid="settings-button"
          aria-label="Settings"
        >
          <Settings size={16} />
        </button>
      </div>
    </header>
  );
}
