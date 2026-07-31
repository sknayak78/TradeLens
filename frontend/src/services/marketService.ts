import { api } from "@/services/api";
import type {
  Opportunity,
  Insight,
  MarketSnapshot,
  TodaysFocusItem,
  Stock,
  Trend,
} from "@/types";

export interface MarketSummary {
  indices: MarketSnapshot[];
  todaysFocus: TodaysFocusItem[];
  status: "open" | "closed";
  asOf: string;
}

export interface StockDetail extends Stock {
  support: number;
  resistance: number;
  aiInsight: string;
  series: { t: string; v: number }[];
}

export interface StockSummary {
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  trend: "bullish" | "bearish" | "neutral";
  sector: string;
}

export const marketService = {
  summary: async (): Promise<MarketSummary> => {
    const { data } = await api.get<MarketSummary>("/market-summary");
    return data;
  },

  opportunities: async (): Promise<Opportunity[]> => {
    const { data } = await api.get<Opportunity[]>("/opportunities");
    return data;
  },

  stock: async (symbol: string): Promise<StockDetail> => {
    const { data } = await api.get<StockDetail>(`/stock/${symbol}`);
    return data;
  },

  searchStocks: async (query: string, limit = 8): Promise<StockSummary[]> => {
    const { data } = await api.get<StockSummary[]>("/stocks", {
      params: { q: query, limit },
    });
    return data;
  },
};

/** Adapter: build an Insight object from a StockDetail (used by the chart card). */
export function stockToInsight(s: StockDetail): Insight {
  const trend: Trend = s.trend;
  return {
    symbol: s.symbol,
    trend,
    support: s.support,
    resistance: s.resistance,
    aiInsight: s.aiInsight,
    series: s.series,
  };
}
