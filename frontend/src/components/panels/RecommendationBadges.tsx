import { HelpCircle } from "lucide-react";
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

export const TONE_ACCENT: Record<Tone, string> = {
  positive: "border-l-[#26a69a]",
  info: "border-l-[#2962ff]",
  warning: "border-l-[#f5a623]",
  negative: "border-l-[#ef5350]",
  muted: "border-l-[#2a2e39]",
};

export const ACTION_TONE: Record<RecommendationAction, Tone> = {
  "Strong Buy": "positive",
  Buy: "positive",
  Watch: "info",
  Wait: "warning",
  Avoid: "negative",
};

const TONE_TEXT: Record<Tone, string> = {
  positive: "text-[#26a69a]",
  info: "text-[#2962ff]",
  warning: "text-[#f5a623]",
  negative: "text-[#ef5350]",
  muted: "text-[#d1d4dc]",
};

/** "Buy today" phrasing, so the action reads as an instruction. */
const ACTION_HEADLINE: Record<RecommendationAction, string> = {
  "Strong Buy": "Strong Buy Today",
  Buy: "Buy Today",
  Watch: "Watch",
  Wait: "Wait",
  Avoid: "Avoid",
};

/** The action, as the loudest element on the panel. */
export function ActionHeadline({
  action,
  icon,
  testId,
}: {
  action: RecommendationAction;
  icon: ReactNode;
  testId?: string;
}) {
  const tone = ACTION_TONE[action] ?? "muted";
  return (
    <div
      data-testid={testId}
      data-action={action}
      className={`inline-flex items-center gap-3 px-4 py-2.5 rounded-[6px] border-2 ${TONE_STYLE[tone]}`}
    >
      <span className="flex shrink-0">{icon}</span>
      <span className="text-xl md:text-2xl font-bold uppercase tracking-[0.08em] leading-none">
        {ACTION_HEADLINE[action] ?? action}
      </span>
    </div>
  );
}

/** Small labelled chip used for strategy, confidence and data quality. */
export function MetaBadge({
  label,
  value,
  tone = "muted",
  hint,
  testId,
}: {
  label: string;
  value: string;
  tone?: Tone;
  /** Hover/focus explanation, e.g. what confidence actually measures. */
  hint?: string;
  testId?: string;
}) {
  return (
    <span
      data-testid={testId}
      title={hint}
      tabIndex={hint ? 0 : undefined}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider ${TONE_STYLE[tone]} ${
        hint ? "cursor-help" : ""
      }`}
    >
      <span className="text-[#787b86]">{label}</span>
      <span className="font-semibold">{value}</span>
      {hint && <HelpCircle size={11} className="text-[#787b86]" />}
    </span>
  );
}

/** Label + value tile, the building block of the trading plan grid. */
export function LevelTile({
  label,
  value,
  valueClass = "text-white",
  note,
  emphasis = false,
  testId,
}: {
  label: string;
  value: ReactNode;
  valueClass?: string;
  /** Plain-English reading of the number, e.g. "Below preferred threshold". */
  note?: { text: string; tone: Tone };
  /** Marks a value a trader acts on directly (entry, stop, targets). */
  emphasis?: boolean;
  testId?: string;
}) {
  return (
    <div
      className={`rounded-[4px] border bg-[#1a1f2b] px-3 py-2.5 ${
        emphasis ? "border-[#3a3f4b]" : "border-[#2a2e39]"
      }`}
    >
      <div className="text-[9px] uppercase tracking-widest text-[#787b86] mb-1">
        {label}
      </div>
      <div
        className={`font-mono tabular-nums font-bold leading-tight ${
          emphasis ? "text-lg md:text-xl" : "text-base md:text-lg"
        } ${valueClass}`}
        data-testid={testId}
      >
        {value}
      </div>
      {note && (
        <div className={`text-[10px] mt-1 ${TONE_TEXT[note.tone]}`}>
          {note.text}
        </div>
      )}
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
