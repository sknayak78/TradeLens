import { api } from "@/services/api";

export type TradeSide = "LONG" | "SHORT";
export type TradeStatus = "OPEN" | "CLOSED";

export interface MentorSnapshot {
  action: string | null;
  strategy: string | null;
  entry_range_low: number | null;
  entry_range_high: number | null;
  actual_entry_price: number | null;
  planned_stop_loss: number | null;
  target_1: number | null;
  target_2: number | null;
  risk_reward: number | null;
  holding_period: string | null;
  reason: string | null;
  captured_at: string | null;
}

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
  mentor_snapshot: MentorSnapshot | null;
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

export interface TradeUpdatePayload {
  trade_date?: string;
  side?: TradeSide;
  entry_price?: number;
  exit_price?: number | null;
  exit_date?: string | null;
  quantity?: number;
  notes?: string;
  confirm_out_of_range?: boolean;
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

  update: async (id: number, payload: TradeUpdatePayload): Promise<Trade> => {
    const { data } = await api.put<Trade>(`/trades/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await api.delete(`/trades/${id}`);
  },
};
