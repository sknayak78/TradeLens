import type { Trend, TradeSetup, RiskLevel } from "@/types";

interface BadgeProps {
  label: string;
  value: string;
  dot: string;
  color: string;
  testId?: string;
}

function Badge({ label, value, dot, color, testId }: BadgeProps) {
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider ${color}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      <span className="text-[#787b86]">{label}</span>
      <span className="font-semibold">{value}</span>
    </span>
  );
}

const TREND_STYLE: Record<Trend, string> = {
  bullish: "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25",
  bearish: "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25",
  neutral: "text-[#787b86] bg-[#787b86]/10 border-[#787b86]/25",
};

const RISK_STYLE: Record<RiskLevel, string> = {
  Low: "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25",
  Medium: "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25",
  High: "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25",
};

const RISK_DOT: Record<RiskLevel, string> = {
  Low: "bg-[#26a69a]",
  Medium: "bg-[#f5a623]",
  High: "bg-[#ef5350]",
};

const SETUP_STYLE =
  "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25";

interface AnalysisBadgesProps {
  trend: Trend;
  setup: TradeSetup;
  risk: RiskLevel;
  size?: "sm" | "xs";
  layout?: "row" | "wrap";
  testIdPrefix?: string;
}

const TREND_LABEL: Record<Trend, string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Neutral",
};

export default function AnalysisBadges({
  trend,
  setup,
  risk,
  layout = "wrap",
  testIdPrefix = "badge",
}: AnalysisBadgesProps) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 ${
        layout === "wrap" ? "flex-wrap" : "flex-nowrap whitespace-nowrap"
      }`}
      data-testid={`${testIdPrefix}-group`}
    >
      <Badge
        label="Trend"
        value={TREND_LABEL[trend]}
        dot={
          trend === "bullish"
            ? "bg-[#26a69a]"
            : trend === "bearish"
              ? "bg-[#ef5350]"
              : "bg-[#787b86]"
        }
        color={TREND_STYLE[trend]}
        testId={`${testIdPrefix}-trend`}
      />
      <Badge
        label="Setup"
        value={setup}
        dot="bg-[#f5a623]"
        color={SETUP_STYLE}
        testId={`${testIdPrefix}-setup`}
      />
      <Badge
        label="Risk"
        value={risk}
        dot={RISK_DOT[risk]}
        color={RISK_STYLE[risk]}
        testId={`${testIdPrefix}-risk`}
      />
    </div>
  );
}

export function Stars({ count, testId }: { count: number; testId?: string }) {
  const filled = Math.max(0, Math.min(5, count));
  return (
    <span
      className="inline-flex tracking-tight text-[#f5a623] font-mono text-[13px] leading-none"
      data-testid={testId}
      aria-label={`${filled} out of 5 stars`}
    >
      {"★".repeat(filled)}
      <span className="text-[#2a2e39]">{"★".repeat(5 - filled)}</span>
    </span>
  );
}

const ACTION_STYLE: Record<string, string> = {
  "Buy on Breakout": "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/25",
  "Watch": "text-[#2962ff] bg-[#2962ff]/10 border-[#2962ff]/25",
  "Wait": "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/25",
  "Avoid": "text-[#ef5350] bg-[#ef5350]/10 border-[#ef5350]/25",
};

export function ActionPill({
  action,
  testId,
}: {
  action: string;
  testId?: string;
}) {
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center px-2 py-0.5 rounded-[3px] border text-[10px] font-mono uppercase tracking-wider ${
        ACTION_STYLE[action] || "text-[#d1d4dc] bg-[#2a2e39]/40 border-[#2a2e39]"
      }`}
    >
      {action}
    </span>
  );
}
