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

export function getInsight(symbol: string): Promise<Insight | undefined> {
  const list = insightsData.insights as Insight[];
  const match = list.find((i) => i.symbol === symbol) ?? list[0];
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
