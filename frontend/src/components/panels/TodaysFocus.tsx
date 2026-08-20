import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { useMarketSummary } from "@/hooks/useMarket";
import type { TodaysFocusItem } from "@/types";
import { Flame, TrendingUp, Radar, Ban } from "lucide-react";

const ICONS: Record<TodaysFocusItem["key"], typeof Flame> = {
  bestSetup: Flame,
  momentum: TrendingUp,
  breakout: Radar,
  avoid: Ban,
};

const ACCENTS: Record<TodaysFocusItem["key"], string> = {
  bestSetup: "text-[#2962ff] bg-[#2962ff]/10 border-[#2962ff]/25",
  momentum: "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25",
  breakout: "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25",
  avoid: "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25",
};

export default function TodaysFocus() {
  const { data, isLoading, isError, error, refetch } = useMarketSummary();

  return (
    <PanelCard
      title="Today's Focus"
      subtitle="Curated setups & warnings"
      testId="card-todays-focus"
    >
      {isLoading && <LoadingState testId="focus-loading" />}
      {isError && (
        <ErrorState
          message={error?.message ?? "Failed to load focus items."}
          onRetry={() => refetch()}
          testId="focus-error"
        />
      )}
      {!isLoading && !isError && data && data.todaysFocus.length === 0 && (
        <EmptyState
          title="No focus items today"
          description="Curated setups will appear once available."
          testId="focus-empty"
        />
      )}
      {!isLoading && !isError && data && data.todaysFocus.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {data.todaysFocus.map((item) => {
            const Icon = ICONS[item.key];
            const isDown = item.changePct < 0;
            return (
              <div
                key={item.key}
                data-testid={`focus-${item.key}`}
                className="rounded-[4px] border border-[#D9DDE2] bg-white p-3 flex flex-col gap-2 hover:border-[#C5CAD3] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[3px] border text-[10px] uppercase tracking-widest font-semibold ${ACCENTS[item.key]}`}
                  >
                    <Icon size={11} strokeWidth={2.5} />
                    {item.label}
                  </span>
                  <span
                    className={`font-mono tabular-nums text-xs ${
                      isDown ? "text-[#ef5350]" : "text-[#26a69a]"
                    }`}
                  >
                    {item.changePct >= 0 ? "+" : ""}
                    {item.changePct.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-baseline justify-between gap-2">
                  <span
                    className="text-[#1F2933] text-base font-semibold tracking-tight"
                    data-testid={`focus-${item.key}-symbol`}
                  >
                    {item.symbol}
                  </span>
                  <span className="text-[11px] text-[#667085] truncate max-w-[130px] text-right">
                    {item.name}
                  </span>
                </div>
                <p className="text-[12px] leading-relaxed text-[#a3a6af]">
                  {item.note}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </PanelCard>
  );
}
