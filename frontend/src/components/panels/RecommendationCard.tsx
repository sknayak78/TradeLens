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
  LevelTile,
  ReasonList,
  TONE_ACCENT,
  Tone,
} from "@/components/panels/RecommendationBadges";
import EducationalDisclaimer, {
  RECOMMENDATION_CONTEXT_MESSAGE,
} from "@/components/common/EducationalDisclaimer";
import MetricHelp from "@/components/common/MetricHelp";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

/** Presentation-only reading of the engine's risk/reward number. */
function riskRewardNote(ratio: number): { text: string; tone: Tone } {
  if (ratio >= 2.5) return { text: "Excellent", tone: "positive" };
  if (ratio >= 1.5) return { text: "Good", tone: "positive" };
  if (ratio >= 1) return { text: "Acceptable", tone: "warning" };
  return { text: "Below preferred threshold", tone: "negative" };
}

function normalise(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, "");
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
 * Progressive-disclosure view of the Mentor recommendation. All engine fields are
 * preserved; detail is organised into collapsible sections for easier scanning.
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
    beginnerTip,
    idealFor,
    why,
    positives,
    risks,
    levels,
    rationale,
    rulesMatched,
    warnings,
  } = recommendation;

  const tone = ACTION_TONE[action] ?? "muted";
  const shown = new Set(positives.map(normalise));
  const keyReasons = why.filter((reason) => !shown.has(normalise(reason)));

  return (
    <div className="flex flex-col gap-3" data-testid="recommendation-card">
      <Accordion
        type="multiple"
        defaultValue={[]}
        className="rounded-[4px] border border-[#D9DDE2] bg-white"
      >
        <AccordionItem value="overview" className="border-[#D9DDE2] px-4">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Info size={12} />
              Overview
            </span>
          </AccordionTrigger>
          <AccordionContent className={`pb-4 border-l-2 pl-3 ${TONE_ACCENT[tone]}`}>
            <p
              className="text-[#1F2933] text-base md:text-lg font-semibold leading-snug"
              data-testid="recommendation-verdict"
            >
              {verdict}
            </p>
            <p
              className="text-[13px] text-[#1F2933] leading-relaxed mt-2"
              data-testid="recommendation-summary"
            >
              {summary}
            </p>
            <p className="text-[11px] text-[#667085] leading-relaxed mt-3">
              {RECOMMENDATION_CONTEXT_MESSAGE}
            </p>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="technical" className="border-[#D9DDE2] px-4">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Compass size={12} />
              Technical picture
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-4">
            {rationale && (
              <p className="text-[13px] text-[#1F2933] leading-relaxed mb-3">
                {rationale}
              </p>
            )}
            {rulesMatched.length > 0 && (
              <ul className="space-y-1.5 text-[13px] text-[#1F2933]">
                {rulesMatched.map((rule) => (
                  <li key={rule} className="flex gap-2">
                    <CheckCircle2 size={12} className="text-[#26a69a] shrink-0 mt-0.5" />
                    <span>{rule}</span>
                  </li>
                ))}
              </ul>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="plan" className="border-[#D9DDE2] px-4">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Target size={12} />
              Trading setup
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-4" data-testid="recommendation-plan">
            <p
              className="text-[13px] text-[#1F2933] leading-relaxed mb-3"
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
                    labelHelp={
                      levels ? (
                        <MetricHelp
                          metric="riskReward"
                          context={{ riskReward: levels.riskReward }}
                          testId="recommendation-risk-reward-help"
                        />
                      ) : (
                        <MetricHelp metric="riskReward" testId="recommendation-risk-reward-help" />
                      )
                    }
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
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="reasoning" className="border-[#D9DDE2] px-4">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Info size={12} />
              Market context
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-4" data-testid="recommendation-reasoning">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <ReasonList
                title="Strengths"
                items={positives}
                icon={<CheckCircle2 size={12} />}
                tone="positive"
                testId="recommendation-positives"
              />
              <ReasonList
                title="Key Reasons"
                items={keyReasons}
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
            {warnings.length > 0 && (
              <div className="mt-3 rounded-[4px] border border-[#f5a623]/25 bg-[#f5a623]/5 p-3">
                <div className="text-[10px] uppercase tracking-widest text-[#f5a623] mb-2">
                  Warnings
                </div>
                <ul className="space-y-1.5 text-[13px] text-[#1F2933]">
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="lesson" className="border-0 px-4">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <GraduationCap size={12} />
              Mentor lesson
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-4" data-testid="recommendation-beginner">
            <p
              className="text-[13px] text-[#1F2933] leading-relaxed"
              data-testid="recommendation-beginner-tip"
            >
              {beginnerTip}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
              <div className="rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] px-3 py-2">
                <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
                  Watch Next
                </div>
                <div
                  className="text-[13px] text-[#1F2933]"
                  data-testid="recommendation-next-trigger"
                >
                  {nextTrigger}
                </div>
              </div>
              <div className="rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] px-3 py-2">
                <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
                  Ideal For
                </div>
                <div
                  className="text-[13px] text-[#1F2933]"
                  data-testid="recommendation-ideal-for"
                >
                  {idealFor}
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <EducationalDisclaimer variant="inline" testId="recommendation-disclaimer" />
    </div>
  );
}
