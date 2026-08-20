import { api } from "@/services/api";

export type TradeSide = "LONG" | "SHORT";
export type TradeStatus = "OPEN" | "CLOSED";

export interface Trade {
  id: number;
  trade_date: string;
  symbol: string;
  side: TradeSide;
  entry_price: number;
  exit_price: number | null;
  exit_date: string | null;
  quantity: number;
  notes: string;
  status: TradeStatus;
  pnl: number;
  unrealized_pnl: number | null;
  current_price: number | null;
  holding_period_days: number | null;
}

export interface TradeCreatePayload {
  trade_date: string;
  symbol: string;
  side: TradeSide;
  entry_price: number;
  exit_price?: number | null;
  exit_date?: string | null;
  quantity: number;
  notes?: string;
  confirm_out_of_range?: boolean;
}

export interface TradeUpdatePayload extends TradeCreatePayload {}

export const tradeService = {
  list: async (): Promise<Trade[]> => {
    const { data } = await api.get<Trade[]>("/trades");
    return data;
  },

  create: async (payload: TradeCreatePayload): Promise<Trade> => {
    const { data } = await api.post<Trade>("/trades", payload);
    return data;
  },

  update: async (id: number, payload: TradeUpdatePayload): Promise<Trade> => {
    const { data } = await api.put<Trade>(`/trades/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await api.delete(`/trades/${id}`);
  },
};
