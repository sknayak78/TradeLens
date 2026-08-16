import { useQuery, UseQueryResult } from "@tanstack/react-query";
import {
  marketService,
  MarketSummary,
  OpportunitiesResponse,
  StockDetail,
} from "@/services/marketService";
import type { Ranking } from "@/types";

export const MARKET_SUMMARY_KEY = ["market", "summary"] as const;
export const OPPORTUNITIES_KEY = ["market", "opportunities"] as const;
export const stockKey = (symbol: string) => ["market", "stock", symbol] as const;

export function useMarketSummary(): UseQueryResult<MarketSummary, Error> {
  return useQuery({
    queryKey: MARKET_SUMMARY_KEY,
    queryFn: marketService.summary,
  });
}

export function useRankings(): UseQueryResult<OpportunitiesResponse, Error> {
  return useQuery({
    queryKey: OPPORTUNITIES_KEY,
    queryFn: marketService.opportunities,
  });
}

// Legacy alias — kept so nothing else breaks.
export const useOpportunities = useRankings;

export function useStock(symbol: string): UseQueryResult<StockDetail, Error> {
  return useQuery({
    queryKey: stockKey(symbol),
    queryFn: () => marketService.stock(symbol),
    enabled: Boolean(symbol),
  });
}
