import { createContext, useContext, useMemo, ReactNode } from "react";
import {
  useSettingsQuery,
  useUpdateSettings,
} from "@/hooks/useSettings";
import type { AppSettings, AppSettingsUpdate } from "@/services/settingsService";

interface SettingsContextValue {
  settings: AppSettings | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  update: (payload: AppSettingsUpdate) => void;
  isUpdating: boolean;
}

const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const query = useSettingsQuery();
  const mutation = useUpdateSettings();

  const value = useMemo<SettingsContextValue>(
    () => ({
      settings: query.data,
      isLoading: query.isLoading,
      isError: query.isError,
      error: query.error,
      refetch: () => query.refetch(),
      update: (payload) => mutation.mutate(payload),
      isUpdating: mutation.isPending,
    }),
    [query.data, query.isLoading, query.isError, query.error, query.refetch, mutation],
  );

  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useAppSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useAppSettings must be used within a SettingsProvider");
  }
  return ctx;
}
