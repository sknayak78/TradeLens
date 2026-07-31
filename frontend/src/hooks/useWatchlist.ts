import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
} from "@tanstack/react-query";
import { watchlistService } from "@/services/watchlistService";
import type { WatchItem } from "@/types";

export const WATCHLIST_QUERY_KEY = ["watchlist"] as const;

export function useWatchlist(): UseQueryResult<WatchItem[], Error> {
  return useQuery({
    queryKey: WATCHLIST_QUERY_KEY,
    queryFn: watchlistService.list,
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => watchlistService.add(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY }),
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => watchlistService.remove(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY }),
  });
}
