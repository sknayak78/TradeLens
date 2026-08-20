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
export const stockKey = (symbol: string, timeframe: string) =>
  ["market", "stock", symbol, timeframe] as const;
export const dayRangeKey = (symbol: string, date: string) =>
  ["market", "day-range", symbol, date] as const;

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
    staleTime: 60_000,
    retry: 2,
  });
}

// Legacy alias — kept so nothing else breaks.
export const useOpportunities = useRankings;

export function useStock(
  symbol: string,
  timeframe: string,
): UseQueryResult<StockDetail, Error> {
  return useQuery({
    queryKey: stockKey(symbol, timeframe),
    queryFn: () => marketService.stock(symbol, timeframe),
    enabled: Boolean(symbol),
  });
}

export function useDayRange(symbol: string, date: string, enabled = true) {
  return useQuery({
    queryKey: dayRangeKey(symbol, date),
    queryFn: () => marketService.dayRange(symbol, date),
    enabled: enabled && Boolean(symbol && date),
  });
}
