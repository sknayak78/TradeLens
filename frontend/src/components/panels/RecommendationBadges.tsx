import type { ReactNode } from "react";
import type { RecommendationAction } from "@/types";

/** Tone palette shared by every recommendation surface. */
export type Tone = "positive" | "info" | "warning" | "negative" | "muted";

const TONE_STYLE: Record<Tone, string> = {
  positive: "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/30",
  info: "text-[#2962ff] bg-[#2962ff]/10 border-[#2962ff]/30",
  warning: "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/30",
  negative: "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/30",
  muted: "text-[#d1d4dc] bg-[#787b86]/10 border-[#2a2e39]",
};

const TONE_FILL: Record<Tone, string> = {
  positive: "bg-[#26a69a]",
  info: "bg-[#2962ff]",
  warning: "bg-[#f5a623]",
  negative: "bg-[#ef5350]",
  muted: "bg-[#787b86]",
};

export const ACTION_TONE: Record<RecommendationAction, Tone> = {
  "Strong Buy": "positive",
  Buy: "positive",
  Watch: "info",
  Wait: "warning",
  Avoid: "negative",
};

/** The headline verdict pill — the loudest element on the card. */
export function ActionBadge({
  action,
  testId,
}: {
  action: RecommendationAction;
  testId?: string;
}) {
  const tone = ACTION_TONE[action] ?? "muted";
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-[4px] border text-sm font-semibold uppercase tracking-[0.12em] ${TONE_STYLE[tone]}`}
    >
      <span className={`w-2 h-2 rounded-full ${TONE_FILL[tone]}`} />
      {action}
    </span>
  );
}

/** Small labelled chip used for strategy, confidence and data quality. */
export function MetaBadge({
  label,
  value,
  tone = "muted",
  testId,
}: {
  label: string;
  value: string;
  tone?: Tone;
  testId?: string;
}) {
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider ${TONE_STYLE[tone]}`}
    >
      <span className="text-[#787b86]">{label}</span>
      <span className="font-semibold">{value}</span>
    </span>
  );
}

/** Label + value tile, the building block of the trading plan grid. */
export function LevelTile({
  label,
  value,
  valueClass = "text-[#d1d4dc]",
  testId,
}: {
  label: string;
  value: ReactNode;
  valueClass?: string;
  testId?: string;
}) {
  return (
    <div className="rounded-[4px] border border-[#2a2e39] bg-[#131722] px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
        {label}
      </div>
      <div
        className={`font-mono tabular-nums text-sm font-semibold ${valueClass}`}
        data-testid={testId}
      >
        {value}
      </div>
    </div>
  );
}

/** Icon + bulleted list block used for positives, reasons and risks. */
export function ReasonList({
  title,
  items,
  icon,
  tone,
  testId,
}: {
  title: string;
  items: string[];
  icon: ReactNode;
  tone: Tone;
  testId?: string;
}) {
  if (!items.length) return null;
  return (
    <div
      className="rounded-[4px] border border-[#2a2e39] bg-[#131722] p-3"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`${TONE_STYLE[tone]} rounded-[3px] border p-1 flex`}>
          {icon}
        </span>
        <span className="text-[10px] uppercase tracking-widest text-[#787b86]">
          {title}
        </span>
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((item) => (
          <li
            key={item}
            className="flex gap-2 text-[13px] leading-relaxed text-[#d1d4dc]"
          >
            <span className={`mt-1.5 w-1 h-1 rounded-full shrink-0 ${TONE_FILL[tone]}`} />
            <span className="min-w-0">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
