import { useState } from "react";
import { FlaskConical, Info, ListChecks, Play } from "lucide-react";
import { InfoCard, InfoSection } from "@/components/layout/InfoPageLayout";
import { CaseCard, type CaseCardState } from "@/components/learning/CaseCard";
import { CaseShell } from "@/components/learning/CaseShell";
import { EvidencePanel } from "@/components/learning/EvidencePanel";
import { LearningProgress } from "@/components/learning/LearningProgress";
import { MentorReveal } from "@/components/learning/MentorReveal";
import { OutcomeReveal } from "@/components/learning/OutcomeReveal";
import { SelfAssessment } from "@/components/learning/SelfAssessment";
import { StopLossPlay } from "@/components/learning/StopLossPlay";
import { TakeawayPanel } from "@/components/learning/TakeawayPanel";
import { YourCallSelect } from "@/components/learning/YourCallSelect";
import { useLearningProgress } from "@/context/LearningProgressContext";
import { TRADELENS_MENTOR } from "@/lib/mentorPresentation";
import {
  CASES,
  CASE_BY_ID,
  caseDecisionLabels,
  caseDecisionAgreement,
  type CaseId,
  type Confidence,
  type DecisionAction,
  type DecisionSubmission,
} from "@/lib/howToUseLessons";

/**
 * "Learn TradeLens by Doing — the Case Lab" (ER-0043 v2). Ten realistic case
 * studies replace the earlier quiz-style lessons. Each case follows:
 * OBSERVE → ANALYSE → FORM A VIEW → MAKE A DECISION → REVEAL MENTOR VIEW →
 * UNDERSTAND THE REASONING → SEE WHAT HAPPENED → LEARN. Mentor/evidence/outcome
 * content is never revealed before the learner submits their own call.
 */
export default function HowToUsePage() {
  const [activeCaseId, setActiveCaseId] = useState<CaseId | null>(null);

  return (
    <div data-testid="how-to-use-page">
      {activeCaseId === null ? (
        <CaseLanding onOpenCase={setActiveCaseId} />
      ) : (
        <CaseView
          caseId={activeCaseId}
          onBackToList={() => setActiveCaseId(null)}
          onOpenCase={setActiveCaseId}
        />
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Landing
 * ------------------------------------------------------------------------- */

function CaseLanding({ onOpenCase }: { onOpenCase: (id: CaseId) => void }) {
  const { completed, completedCount, totalLessons, resetProgress } =
    useLearningProgress();

  const recommended = CASES.find((c) => !completed.includes(c.id))?.id;

  return (
    <div className="space-y-4">
      <div
        data-testid="case-landing"
        className="rounded-[4px] border border-[#2962ff]/25 bg-gradient-to-br from-[#F6F7F5] to-[#2962ff]/[0.04] p-5"
      >
        <div className="flex items-center gap-2">
          <FlaskConical size={22} className="text-[#2962ff]" />
          <h2 className="text-xl font-semibold text-[#1F2933] tracking-tight">
            The TradeLens Case Lab
          </h2>
        </div>
        <p className="mt-1 max-w-3xl text-sm text-[#667085]">
          Learn how to evaluate a trading setup by working through 10 realistic
          situations. Each case asks you to observe, form your own view and make
          a call — then reveals the evidence, the Mentor's reasoning and what
          happened next.
        </p>
        <p className="mt-2 text-xs text-[#C5CAD3]">
          TradeLens teaches you to reason about a setup — it never tells you
          what to buy.
        </p>
      </div>

      <LearningProgress
        completedCount={completedCount}
        totalLessons={totalLessons}
        onReset={resetProgress}
      />

      <div className="flex items-center gap-2">
        <ListChecks size={15} className="text-[#2962ff]" />
        <span className="text-[10px] uppercase tracking-widest text-[#667085]">
          Your learning journey
        </span>
        {recommended && (
          <button
            type="button"
            onClick={() => onOpenCase(recommended)}
            data-testid="case-start-next"
            className="ml-auto inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium text-white bg-[#2962ff] hover:bg-[#2962ff]/85 transition-colors"
          >
            <Play size={11} /> Continue with the next case
          </button>
        )}
      </div>

      <div
        data-testid="case-cards-grid"
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        {CASES.map((caseStudy) => {
          const state: CaseCardState = completed.includes(caseStudy.id)
            ? "completed"
            : caseStudy.id === recommended
              ? "current"
              : "not-started";
          return (
            <CaseCard
              key={caseStudy.id}
              caseStudy={caseStudy}
              state={state}
              onClick={() => onOpenCase(caseStudy.id)}
            />
          );
        })}
      </div>

      {/* Preserved reference content from the earlier How-to-Use guide */}
      <ReferenceGuide />
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Case view
 * ------------------------------------------------------------------------- */

function CaseView({
  caseId,
  onBackToList,
  onOpenCase,
}: {
  caseId: CaseId;
  onBackToList: () => void;
  onOpenCase: (id: CaseId) => void;
}) {
  const caseStudy = CASE_BY_ID[caseId];
  const { isComplete, toggleLessonComplete } = useLearningProgress();
  const completed = isComplete(caseStudy.id);

  const [action, setAction] = useState<DecisionAction | null>(null);
  const [confidence, setConfidence] = useState<Confidence | null>(null);
  const [submitted, setSubmitted] = useState(false);
  // Separate flags used by stop-loss / self-assessment interactions which
  // reveal their own completion via a callback rather than a submit button.
  const [playDone, setPlayDone] = useState(false);
  const [revision, setRevision] = useState(0);

  const interaction = caseStudy.interaction;
  const kind = interaction.kind;

  const canSubmit =
    kind === "decision" ? action !== null && confidence !== null : false;

  const canContinue =
    kind === "decision" ? submitted : kind === "stopLoss" || kind === "selfAssessment" ? playDone : false;

  const revealed = kind === "decision" ? submitted : kind === "stopLoss" || kind === "selfAssessment" ? playDone : false;

  const previousCase = CASES[caseStudy.number - 2];
  const nextCase = CASES[caseStudy.number];

  const comparison =
    revealed && kind === "decision" && action
      ? {
          learner: { action, confidence: confidence ?? "Medium" } satisfies DecisionSubmission,
          mentor: caseStudy.mentorView,
          agreement: caseDecisionAgreement(action, caseStudy.mentorView.action),
        }
      : null;

  function handleSubmit() {
    if (!canSubmit) return;
    if (!completed) toggleLessonComplete(caseStudy.id);
    setSubmitted(true);
  }

  function handlePlayDone() {
    if (!completed) toggleLessonComplete(caseStudy.id);
    setPlayDone(true);
  }

  function handleContinue() {
    if (nextCase) onOpenCase(nextCase.id);
  }

  function handleRestart() {
    setAction(null);
    setConfidence(null);
    setSubmitted(false);
    setPlayDone(false);
    setRevision((r) => r + 1);
  }

  return (
    <CaseShell
      caseStudy={caseStudy}
      onBackToList={onBackToList}
      onPrevious={previousCase ? () => onOpenCase(previousCase.id) : undefined}
      previousNumber={previousCase?.number}
      onContinue={canContinue ? handleContinue : undefined}
      nextNumber={nextCase?.number}
      onRestart={handleRestart}
      continueLabel={canContinue && nextCase ? "Next case" : "Continue"}
      continueDisabled={!canContinue}
      completed={completed}
    >
      {/* Interaction */}
      {kind === "decision" && (
        <div
          data-testid="case-interaction"
          className="rounded-[4px] border border-[#D9DDE2] bg-white p-4"
        >
          <YourCallSelect
            prompt={interaction.prompt}
            action={action}
            setAction={setAction}
            confidence={confidence}
            setConfidence={setConfidence}
            disabled={submitted}
          />
          <div className="mt-4">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              data-testid="case-submit"
              className={`inline-flex items-center gap-1.5 rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                canSubmit
                  ? "bg-[#26a69a] text-white hover:bg-[#26a69a]/85"
                  : "bg-[#E5E7EB] text-[#9CA3AF]"
              }`}
            >
              Submit my call
            </button>
            {!canSubmit && !submitted && (
              <span className="ml-2 text-[11px] text-[#667085]">
                Pick your call and confidence to reveal the reasoning.
              </span>
            )}
          </div>
        </div>
      )}

      {kind === "stopLoss" && (
        <StopLossPlay
          key={revision}
          caseStudy={caseStudy}
          onComplete={handlePlayDone}
        />
      )}

      {kind === "selfAssessment" && (
        <SelfAssessment
          key={revision}
          caseStudy={caseStudy}
          onComplete={handlePlayDone}
        />
      )}

      {/* Reveal-only content (after the learner's own call) */}
      {revealed && (
        <>
          <EvidencePanel evidence={caseStudy.evidence} testId={`evidence-${caseStudy.id}`} />

          {comparison && kind === "decision" && (
            <MentorReveal
              mentor={caseStudy.mentorView}
              learnerAction={comparison.learner.action}
              agreement={comparison.agreement}
              rationale={caseStudy.mentorView.rationale}
              takeaway={caseStudy.mentorView.takeaway}
              testId={`mentor-reveal-${caseStudy.id}`}
            />
          )}

          {(kind === "stopLoss" || kind === "selfAssessment") && (
            <MentorReveal
              mentor={caseStudy.mentorView}
              rationale={caseStudy.mentorView.rationale}
              takeaway={caseStudy.mentorView.takeaway}
              testId={`mentor-reveal-${caseStudy.id}`}
            />
          )}

          {caseStudy.outcome && (
            <OutcomeReveal
              learnerDecision={action ? caseDecisionLabels[action] : "No call"}
              outcomes={caseStudy.outcome.steps}
              decisionPointPrice={caseStudy.outcome.decisionPointPrice}
              testId={`outcome-reveal-${caseStudy.id}`}
            />
          )}

          <TakeawayPanel
            takeaway={caseStudy.takeaway}
            learnWhy={caseStudy.learnWhy}
            testId={`takeaway-${caseStudy.id}`}
          />
        </>
      )}
    </CaseShell>
  );
}

/* ---------------------------------------------------------------------------
 * Reference guide (preserved educational content)
 * ------------------------------------------------------------------------- */

const METRIC_REFERENCE = [
  {
    title: "RSI (Relative Strength Index)",
    detail:
      "A momentum indicator on a 0–100 scale measuring the strength of recent price movements. Higher readings suggest stronger recent buying momentum; lower readings suggest weaker momentum. Use it to sense momentum, not as a standalone buy/sell rule.",
  },
  {
    title: "EMA20 / EMA50 / EMA200",
    detail:
      "Exponential moving averages that emphasise recent sessions. Price above an average is generally supportive on that timeframe; averages stacked EMA20 > EMA50 > EMA200 indicate a bullish alignment. EMAs provide context — they are not independent entry signals.",
  },
  {
    title: "Support & Resistance",
    detail:
      "Price zones where buyers (support) or sellers (resistance) have historically appeared. Location relative to these levels decides how attractive an entry is, not just trend direction.",
  },
  {
    title: "Sufficient Headroom",
    detail:
      "The percentage distance from the current price up to the next resistance level. More headroom can make a setup more attractive; thin headroom means upside may be limited relative to risk. It is calculated from data — not a forecast.",
  },
  {
    title: "Risk / Reward",
    detail:
      "How much you might lose (to a stop) against how much you might gain (to a target). A favourable ratio does not guarantee profit, but an unfavourable one makes a disciplined entry less attractive.",
  },
];

/* Map our four-bucket decisions onto reference definitions for the glossary. */
const ACTION_REFERENCE = [
  {
    name: "Buy",
    summary: "The evidence leans positive, but confirmation still matters.",
    contrast: "More constructive than Watch/WAIT; you are prepared to act near the plan.",
  },
  {
    name: "Watch",
    summary: "Something interesting is developing — observe and track it first.",
    contrast: "More engaged than WAIT; you are tracking a developing case.",
  },
  {
    name: "Wait",
    summary: "Conditions are mixed or the price location is poor right now.",
    contrast: "Silting on your hands is a valid, disciplined position while evidence improves.",
  },
  {
    name: "Avoid",
    summary: "The technical picture is weak or unfavourable for a fresh entry.",
    contrast: "The most cautious fresh-entry view; not a comment on the company forever.",
  },
];

function ReferenceGuide() {
  return (
    <div className="mt-8" data-testid="case-reference">
      <div className="mb-4 flex items-center gap-2">
        <Info size={15} className="text-[#667085]" />
        <span className="text-[10px] uppercase tracking-widest text-[#667085]">
          Reference · the concepts behind the cases
        </span>
      </div>

      <InfoSection title="Metric glossary">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 not-prose">
          {METRIC_REFERENCE.map((metric) => (
            <InfoCard key={metric.title} title={metric.title} accent="border-l-[#2962ff]">
              {metric.detail}
            </InfoCard>
          ))}
        </div>
      </InfoSection>

      <InfoSection title={`The ${TRADELENS_MENTOR} decisions`}>
        <p className="mb-3 text-sm text-[#667085]">
          These are the four choices you make in the case lab. They describe what
          the available technical evidence suggests for learning — not
          personalized investment advice or trade instructions.
        </p>
        <div className="grid grid-cols-1 gap-2 not-prose">
          {ACTION_REFERENCE.map((action) => (
            <InfoCard key={action.name} title={action.name} accent="border-l-[#2962ff]">
              <p className="mt-1">{action.summary}</p>
              <p className="mt-2 text-[#667085] text-xs">{action.contrast}</p>
            </InfoCard>
          ))}
        </div>
      </InfoSection>
    </div>
  );
}
