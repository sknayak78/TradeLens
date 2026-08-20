import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
} from "@tanstack/react-query";
import {
  tradeService,
  Trade,
  TradeCreatePayload,
  TradeUpdatePayload,
} from "@/services/tradeService";

export const TRADES_QUERY_KEY = ["trades"] as const;

export function useTrades(): UseQueryResult<Trade[], Error> {
  return useQuery({
    queryKey: TRADES_QUERY_KEY,
    queryFn: tradeService.list,
  });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TradeCreatePayload) => tradeService.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: TRADES_QUERY_KEY }),
  });
}

export function useUpdateTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TradeUpdatePayload }) =>
      tradeService.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: TRADES_QUERY_KEY }),
  });
}

export function useDeleteTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => tradeService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: TRADES_QUERY_KEY }),
  });
}
