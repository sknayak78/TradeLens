import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
} from "@tanstack/react-query";
import {
  settingsService,
  AppSettings,
  AppSettingsUpdate,
} from "@/services/settingsService";

export const SETTINGS_QUERY_KEY = ["settings"] as const;

export function useSettingsQuery(): UseQueryResult<AppSettings, Error> {
  return useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: settingsService.get,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AppSettingsUpdate) => settingsService.update(payload),
    onSuccess: (data) => qc.setQueryData(SETTINGS_QUERY_KEY, data),
  });
}
