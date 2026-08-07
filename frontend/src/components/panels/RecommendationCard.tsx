import {
  AlertTriangle,
  BookOpen,
  Eye,
  RefreshCw,
  Target,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Recommendation } from "@/types";
import {
  ACTION_TONE,
  LevelTile,
  TONE_ACCENT,
  Tone,
} from "@/components/panels/RecommendationBadges";

/** Presentation-only reading of the engine's risk/reward number. */
function riskRewardNote(ratio: number): { text: string; tone: Tone } {
  if (ratio >= 2.5) return { text: "Excellent", tone: "positive" };
  if (ratio >= 1.5) return { text: "Good", tone: "positive" };
  if (ratio >= 1) return { text: "Acceptable", tone: "warning" };
  return { text: "Below preferred threshold", tone: "negative" };
}

function money(value: number): string {
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
}

/**
 * Insight v2 — educational mentor conversation.
 *
 * Section purposes (one job each):
 * 1. Opening — verdict + summary (what to do)
 * 2. Mentor's Lesson — one trading principle
 * 3. Trading Plan — how to execute
 * 4. Evidence — why this call (compact)
 * 5. What would change my view? — thesis invalidation
 * 6. Who is this for? + Watch Next — audience + operational trigger
 */
export default function RecommendationCard({
  recommendation,
}: RecommendationCardProps) {
  const {
    action,
    verdict,
    summary,
    holdingPeriod,
    entryCondition,
    nextTrigger,
    idealFor,
    mentorLesson,
    whatWouldChangeMyView,
    why,
    risks,
    levels,
  } = recommendation;

  const tone = ACTION_TONE[action] ?? "muted";
  const evidence = why.slice(0, 3);
  const riskLines = risks.slice(0, 2);

  return (
    <div className="flex flex-col gap-3" data-testid="recommendation-card">
      {/* 1 · Mentor opening */}
      <Card accent={tone} testId="recommendation-decision">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-[#787b86] mb-1.5">
            Mentor
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
      </Card>

      {/* 2 · Mentor's Lesson */}
      <Card testId="recommendation-lesson">
        <SectionTitle icon={<BookOpen size={12} />} label="Mentor's Lesson" />
        <p
          className="text-[13px] text-[#d1d4dc] leading-relaxed"
          data-testid="recommendation-mentor-lesson"
        >
          {mentorLesson}
        </p>
      </Card>

      {/* 3 · Trading Plan */}
      <Card testId="recommendation-plan">
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
                emphasis
                testId="recommendation-entry-range"
              />
              <LevelTile
                label="Stop Loss"
                value={money(levels.stopLoss)}
                valueClass="text-[#ef5350]"
                emphasis
                testId="recommendation-stop-loss"
              />
              <LevelTile
                label="Risk / Reward"
                value={`1 : ${levels.riskReward.toFixed(2)}`}
                note={riskRewardNote(levels.riskReward)}
                testId="recommendation-risk-reward"
              />
              <LevelTile
                label="Target 1"
                value={money(levels.target1)}
                valueClass="text-[#26a69a]"
                emphasis
                testId="recommendation-target-1"
              />
              <LevelTile
                label="Target 2"
                value={money(levels.target2)}
                valueClass="text-[#26a69a]"
                emphasis
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
      </Card>

      {/* 4 · Evidence + risks (compact, not a three-column dump) */}
      <Card testId="recommendation-reasoning">
        <SectionTitle icon={<Eye size={12} />} label="Why this call" />
        <ul
          className="flex flex-col gap-1.5 mb-3"
          data-testid="recommendation-why"
        >
          {evidence.map((line) => (
            <li
              key={line}
              className="text-[13px] text-[#d1d4dc] leading-relaxed pl-3 border-l border-[#2a2e39]"
            >
              {line}
            </li>
          ))}
        </ul>
        {riskLines.length > 0 && (
          <>
            <SectionTitle
              icon={<AlertTriangle size={12} />}
              label="Risks to respect"
            />
            <ul
              className="flex flex-col gap-1.5"
              data-testid="recommendation-risks"
            >
              {riskLines.map((line) => (
                <li
                  key={line}
                  className="text-[13px] text-[#d1d4dc] leading-relaxed pl-3 border-l border-[#ef5350]/40"
                >
                  {line}
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      {/* 5 · What would change my view? */}
      <Card testId="recommendation-change-view">
        <SectionTitle
          icon={<RefreshCw size={12} />}
          label="What would change my view?"
        />
        <p
          className="text-[13px] text-[#d1d4dc] leading-relaxed"
          data-testid="recommendation-what-would-change-my-view"
        >
          {whatWouldChangeMyView}
        </p>
      </Card>

      {/* 6 · Who + Watch Next */}
      <Card testId="recommendation-audience">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <MentorFact
            icon={<Users size={12} />}
            label="Who is this setup for?"
            value={idealFor}
            testId="recommendation-ideal-for"
          />
          <MentorFact
            icon={<Eye size={12} />}
            label="Watch Next"
            value={nextTrigger}
            testId="recommendation-next-trigger"
          />
        </div>
      </Card>
    </div>
  );
}

/** One soft-bordered card, optionally accented with the action's colour. */
function Card({
  children,
  accent,
  testId,
}: {
  children: ReactNode;
  accent?: Tone;
  testId?: string;
}) {
  return (
    <section
      data-testid={testId}
      className={`rounded-[4px] border border-[#2a2e39] bg-[#131722] p-4 ${
        accent ? `border-l-2 ${TONE_ACCENT[accent]}` : ""
      }`}
    >
      {children}
    </section>
  );
}

function SectionTitle({
  icon,
  label,
}: {
  icon: ReactNode;
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

function MentorFact({
  icon,
  label,
  value,
  testId,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="rounded-[3px] border border-[#2a2e39] bg-[#0f1318] px-3 py-2.5 min-w-0">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[#787b86] flex">{icon}</span>
        <span className="text-[10px] uppercase tracking-widest text-[#787b86]">
          {label}
        </span>
      </div>
      <div className="text-[13px] text-[#d1d4dc] leading-relaxed" data-testid={testId}>
        {value}
      </div>
    </div>
  );
}
