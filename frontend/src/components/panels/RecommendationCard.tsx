import {
  AlertTriangle,
  CheckCircle2,
  Compass,
  GraduationCap,
  Info,
  Target,
} from "lucide-react";
import type { Recommendation } from "@/types";
import {
  ACTION_TONE,
  ActionBadge,
  LevelTile,
  MetaBadge,
  ReasonList,
  Tone,
} from "@/components/panels/RecommendationBadges";

const STRATEGY_TONE: Record<string, Tone> = {
  "Fresh Entry": "positive",
  Pullback: "info",
  Breakout: "warning",
  "No Entry Yet": "muted",
};

function money(value: number): string {
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
  symbol?: string;
}

/**
 * The decision-first view of a stock: what to do today, why, at what price and
 * what to watch next.  Renders the API's `recommendation` block verbatim.
 */
export default function RecommendationCard({
  recommendation,
  symbol,
}: RecommendationCardProps) {
  const {
    action,
    strategy,
    verdict,
    summary,
    confidence,
    dataQuality,
    holdingPeriod,
    entryCondition,
    nextTrigger,
    beginnerTip,
    idealFor,
    why,
    positives,
    risks,
    levels,
  } = recommendation;

  const tone = ACTION_TONE[action] ?? "muted";
  const accent = {
    positive: "border-l-[#26a69a]",
    info: "border-l-[#2962ff]",
    warning: "border-l-[#f5a623]",
    negative: "border-l-[#ef5350]",
    muted: "border-l-[#2a2e39]",
  }[tone];

  return (
    <section
      data-testid="recommendation-card"
      data-action={action}
      className={`rounded-[4px] border border-[#2a2e39] border-l-2 ${accent} bg-[#131722] flex flex-col gap-4 p-4`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <ActionBadge action={action} testId="recommendation-action" />
          <MetaBadge
            label="Strategy"
            value={strategy}
            tone={STRATEGY_TONE[strategy] ?? "muted"}
            testId="recommendation-strategy"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <MetaBadge
            label="Confidence"
            value={`${Math.round(confidence * 100)}%`}
            tone={tone}
            testId="recommendation-confidence"
          />
          <MetaBadge
            label="Data"
            value={dataQuality}
            tone={dataQuality === "Complete" ? "muted" : "warning"}
            testId="recommendation-data-quality"
          />
        </div>
      </div>

      {/* Verdict — the first thing a user reads */}
      <div>
        <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
          {symbol ? `${symbol} · Verdict` : "Verdict"}
        </div>
        <p
          className="text-white text-base md:text-lg font-semibold leading-snug"
          data-testid="recommendation-verdict"
        >
          {verdict}
        </p>
        <p
          className="text-[13px] text-[#d1d4dc] leading-relaxed mt-1.5"
          data-testid="recommendation-summary"
        >
          {summary}
        </p>
      </div>

      {/* Trading plan */}
      <div data-testid="recommendation-plan">
        <SectionTitle icon={<Target size={12} />} label="Trading Plan" />
        <p
          className="text-[13px] text-[#d1d4dc] leading-relaxed mb-2"
          data-testid="recommendation-entry-condition"
        >
          {entryCondition}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {levels && (
            <>
              <LevelTile
                label="Entry Range"
                value={`${money(levels.entryMin)} – ${money(levels.entryMax)}`}
                testId="recommendation-entry-range"
              />
              <LevelTile
                label="Stop Loss"
                value={money(levels.stopLoss)}
                valueClass="text-[#ef5350]"
                testId="recommendation-stop-loss"
              />
              <LevelTile
                label="Risk / Reward"
                value={`1 : ${levels.riskReward.toFixed(2)}`}
                testId="recommendation-risk-reward"
              />
              <LevelTile
                label="Target 1"
                value={money(levels.target1)}
                valueClass="text-[#26a69a]"
                testId="recommendation-target-1"
              />
              <LevelTile
                label="Target 2"
                value={money(levels.target2)}
                valueClass="text-[#26a69a]"
                testId="recommendation-target-2"
              />
            </>
          )}
          <LevelTile
            label="Holding Period"
            value={holdingPeriod}
            testId="recommendation-holding-period"
          />
        </div>
      </div>

      {/* Why this recommendation? */}
      <div>
        <SectionTitle
          icon={<Info size={12} />}
          label="Why This Recommendation?"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <ReasonList
            title="Positives"
            items={positives}
            icon={<CheckCircle2 size={12} />}
            tone="positive"
            testId="recommendation-positives"
          />
          <ReasonList
            title="Why"
            items={why}
            icon={<Compass size={12} />}
            tone="info"
            testId="recommendation-why"
          />
          <ReasonList
            title="Risks"
            items={risks}
            icon={<AlertTriangle size={12} />}
            tone="negative"
            testId="recommendation-risks"
          />
        </div>
      </div>

      {/* Beginner section */}
      <div
        className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.07] p-3 flex flex-col gap-2"
        data-testid="recommendation-beginner"
      >
        <div className="flex items-center gap-2">
          <span className="text-[#2962ff] flex">
            <GraduationCap size={14} />
          </span>
          <span className="text-[10px] uppercase tracking-widest text-[#787b86]">
            For Beginners
          </span>
        </div>
        <p
          className="text-[13px] text-[#d1d4dc] leading-relaxed"
          data-testid="recommendation-beginner-tip"
        >
          {beginnerTip}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <BeginnerFact
            label="Watch Next"
            value={nextTrigger}
            testId="recommendation-next-trigger"
          />
          <BeginnerFact
            label="Ideal For"
            value={idealFor}
            testId="recommendation-ideal-for"
          />
        </div>
      </div>
    </section>
  );
}

function SectionTitle({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[#787b86] flex">{icon}</span>
      <span className="text-[10px] uppercase tracking-widest text-[#787b86]">
        {label}
      </span>
    </div>
  );
}

function BeginnerFact({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="rounded-[3px] border border-[#2a2e39] bg-[#131722] px-3 py-2 min-w-0">
      <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1">
        {label}
      </div>
      <div className="text-[13px] text-[#d1d4dc] leading-relaxed" data-testid={testId}>
        {value}
      </div>
    </div>
  );
}
