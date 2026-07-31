import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import type { Trend } from "@/types";

interface TrendBadgeProps {
  trend: Trend;
  value?: number;
  size?: "sm" | "xs";
  testId?: string;
}

export default function TrendBadge({
  trend,
  value,
  size = "xs",
  testId,
}: TrendBadgeProps) {
  const isUp = trend === "bullish";
  const isDown = trend === "bearish";
  const color = isUp
    ? "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25"
    : isDown
      ? "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25"
      : "text-[#787b86] bg-[#787b86]/10 border-[#787b86]/25";
  const Icon = isUp ? ArrowUpRight : isDown ? ArrowDownRight : Minus;
  const label = isUp ? "Bullish" : isDown ? "Bearish" : "Neutral";
  const pad = size === "sm" ? "px-2 py-1 text-xs" : "px-1.5 py-0.5 text-[11px]";

  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 rounded-[3px] border font-mono tabular-nums ${pad} ${color}`}
    >
      <Icon size={size === "sm" ? 12 : 10} />
      <span>{label}</span>
      {typeof value === "number" && (
        <span className="ml-1">
          {value >= 0 ? "+" : ""}
          {value.toFixed(2)}%
        </span>
      )}
    </span>
  );
}
