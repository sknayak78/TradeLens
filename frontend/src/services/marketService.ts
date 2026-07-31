import stocksData from "@/mocks/stocks.json";
import watchlistData from "@/mocks/watchlist.json";
import opportunitiesData from "@/mocks/opportunities.json";
import insightsData from "@/mocks/insights.json";
import marketSnapshotData from "@/mocks/marketSnapshot.json";
import todaysFocusData from "@/mocks/todaysFocus.json";
import settingsData from "@/mocks/settings.json";
import type {
  Stock,
  WatchItem,
  Opportunity,
  Insight,
  MarketSnapshot,
  TodaysFocusItem,
  Settings,
} from "@/types";

/**
 * marketService is the single access point to all mock data.
 * When live APIs are ready, swap the body of each function without touching UI.
 */

function delay<T>(payload: T, ms = 120): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(payload), ms));
}

export function getStocks(): Promise<Stock[]> {
  return delay(stocksData.stocks as Stock[]);
}

export function getWatchlist(): Promise<WatchItem[]> {
  return delay(watchlistData.watchlist as WatchItem[]);
}

export function getOpportunities(): Promise<Opportunity[]> {
  return delay(opportunitiesData.opportunities as Opportunity[]);
}

function synthesizeInsight(symbol: string): Insight {
  const stock = (stocksData.stocks as Stock[]).find((s) => s.symbol === symbol);
  const basePrice = stock?.price ?? 1000;
  const trend = (stock?.trend ?? "neutral") as Insight["trend"];
  const support = +(basePrice * 0.985).toFixed(2);
  const resistance = +(basePrice * 1.02).toFixed(2);
  const start = basePrice * 0.99;
  const times = [
    "09:15", "09:45", "10:15", "10:45", "11:15", "11:45",
    "12:15", "12:45", "13:15", "13:45", "14:15", "14:45", "15:15",
  ];
  const series = times.map((t, i) => {
    const progress = i / (times.length - 1);
    const drift = (basePrice - start) * progress;
    const noise = Math.sin(i * 1.3 + symbol.length) * basePrice * 0.0025;
    return { t, v: +(start + drift + noise).toFixed(2) };
  });
  const trendLabel =
    trend === "bullish" ? "constructive" : trend === "bearish" ? "weak" : "range-bound";
  return {
    symbol,
    trend,
    support,
    resistance,
    aiInsight: `${symbol} is currently ${trendLabel}. Price is trading near ${basePrice.toLocaleString("en-IN")} with support at ${support.toLocaleString("en-IN")} and resistance at ${resistance.toLocaleString("en-IN")}. Wait for confirmation before initiating a position.`,
    series,
  };
}

export function getInsight(symbol: string): Promise<Insight> {
  const list = insightsData.insights as Insight[];
  const match = list.find((i) => i.symbol === symbol) ?? synthesizeInsight(symbol);
  return delay(match);
}

export function getAllInsights(): Promise<Insight[]> {
  return delay(insightsData.insights as Insight[]);
}

export function getMarketSnapshot(): Promise<MarketSnapshot[]> {
  return delay(marketSnapshotData.indices as MarketSnapshot[]);
}

export function getTodaysFocus(): Promise<TodaysFocusItem[]> {
  return delay(todaysFocusData.todaysFocus as TodaysFocusItem[]);
}

export function getSettings(): Promise<Settings> {
  return delay(settingsData as Settings);
}

export function searchStocks(query: string): Promise<Stock[]> {
  const q = query.trim().toLowerCase();
  if (!q) return delay([]);
  const results = (stocksData.stocks as Stock[]).filter(
    (s) =>
      s.symbol.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q),
  );
  return delay(results.slice(0, 8));
}
