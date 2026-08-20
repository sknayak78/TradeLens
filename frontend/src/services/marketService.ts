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

export interface OpportunitiesResponse {
  rankings: Ranking[];
  actionCounts: Record<string, number>;
  provider: string;
  cached: boolean;
  asOf: string;
  marketStatus: "OPEN" | "PRE_OPEN" | "CLOSED" | "WEEKEND";
}

export interface StockDetail extends Stock {
  support: number;
  resistance: number;
  aiInsight: string;
  series: { t: string; v: number }[];
  timeframe?: string;
  timeframeLabel?: string;
  timeframeFallback?: boolean;
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

  opportunities: async (): Promise<OpportunitiesResponse> => {
    const { data } = await api.get<OpportunitiesResponse>("/opportunities", {
      timeout: 60_000,
    });
    return data;
  },

  stock: async (symbol: string, timeframe = "1W"): Promise<StockDetail> => {
    const { data } = await api.get<StockDetail>(`/stock/${symbol}`, {
      params: { timeframe },
    });
    return data;
  },

  dayRange: async (
    symbol: string,
    date: string,
  ): Promise<{
    symbol: string;
    date: string;
    available: boolean;
    low: number | null;
    high: number | null;
    message: string | null;
  }> => {
    const { data } = await api.get(`/stock/${symbol}/day-range`, {
      params: { date },
    });
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
