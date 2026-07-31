import { api } from "@/services/api";

export interface AppSettings {
  id: number;
  capital: number;
  risk_per_trade: number;
  preferred_timeframe: string;
}

export type AppSettingsUpdate = Partial<Omit<AppSettings, "id">>;

export const settingsService = {
  get: async (): Promise<AppSettings> => {
    const { data } = await api.get<AppSettings>("/settings");
    return data;
  },

  update: async (payload: AppSettingsUpdate): Promise<AppSettings> => {
    const { data } = await api.put<AppSettings>("/settings", payload);
    return data;
  },
};
