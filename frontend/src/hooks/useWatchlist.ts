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
    onSuccess: (item) => {
      qc.setQueryData<WatchItem[]>(WATCHLIST_QUERY_KEY, (current = []) => {
        if (current.some((row) => row.symbol === item.symbol)) {
          return current;
        }
        return [...current, item];
      });
      qc.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY });
    },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => watchlistService.remove(symbol),
    onMutate: async (symbol) => {
      await qc.cancelQueries({ queryKey: WATCHLIST_QUERY_KEY });
      const previous = qc.getQueryData<WatchItem[]>(WATCHLIST_QUERY_KEY);
      qc.setQueryData<WatchItem[]>(
        WATCHLIST_QUERY_KEY,
        (current = []) => current.filter((row) => row.symbol !== symbol),
      );
      return { previous };
    },
    onError: (_error, _symbol, context) => {
      if (context?.previous) {
        qc.setQueryData(WATCHLIST_QUERY_KEY, context.previous);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY });
    },
  });
}
