import { api } from "@/services/api";
import type {
  MarketSnapshot,
  TodaysFocusItem,
  Stock,
  Trend,
  Insight,
  Ranking,
  Recommendation,
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
  // Analysis
  strengthScore: number;
  stars: number;
  classification: string;
  tradeSetup:
    | "Momentum"
    | "Breakout"
    | "Pullback"
    | "Trend Continuation"
    | "Consolidation";
  riskLevel: "Low" | "Medium" | "High";
  suggestedAction: "Watch" | "Buy on Breakout" | "Wait" | "Avoid";
  insight: string;
  /** Authoritative decision block; absent on older backends or unusable data. */
  recommendation?: Recommendation | null;
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

  opportunities: async (): Promise<Ranking[]> => {
    const { data } = await api.get<Ranking[]>("/opportunities");
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
