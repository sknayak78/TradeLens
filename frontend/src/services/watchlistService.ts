import { api } from "@/services/api";
import type { WatchItem } from "@/types";

export const watchlistService = {
  list: async (): Promise<WatchItem[]> => {
    const { data } = await api.get<WatchItem[]>("/watchlist");
    return data;
  },

  add: async (symbol: string): Promise<WatchItem> => {
    const { data } = await api.post<WatchItem>("/watchlist", { symbol });
    return data;
  },

  remove: async (symbol: string): Promise<void> => {
    await api.delete(`/watchlist/${symbol}`);
  },
};
