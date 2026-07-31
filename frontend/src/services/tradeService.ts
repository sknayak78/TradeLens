import { api } from "@/services/api";

export interface Trade {
  id: number;
  trade_date: string;
  symbol: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  notes: string;
  pnl: number;
  side: "LONG" | "SHORT";
}

export interface TradeCreatePayload {
  trade_date: string;
  symbol: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  notes?: string;
}

export const tradeService = {
  list: async (): Promise<Trade[]> => {
    const { data } = await api.get<Trade[]>("/trades");
    return data;
  },

  create: async (payload: TradeCreatePayload): Promise<Trade> => {
    const { data } = await api.post<Trade>("/trades", payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await api.delete(`/trades/${id}`);
  },
};
