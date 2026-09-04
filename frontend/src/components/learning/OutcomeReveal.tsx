import { TrendingUp, Wallet } from "lucide-react";
import { caseDecisionLabels, type CaseOutcomeStep } from "@/lib/howToUseLessons";

interface OutcomeRevealProps {
  learnerDecision: string;
  outcomes: CaseOutcomeStep[];
  decisionPointPrice: number;
  testId?: string;
}

function decisionLabel(value: string): string {
  const upper = value.toUpperCase();
  if (upper in caseDecisionLabels) return caseDecisionLabels[upper as keyof typeof caseDecisionLabels];
  return value;
}

/**
 * Lesson 8 outcome reveal — shown only after the learner commits to a decision
 * based on information available at the time. Uses deterministic educational
 * scenario data, not a live backtest.
 */
export function OutcomeReveal({
  learnerDecision,
  outcomes,
  decisionPointPrice,
  testId = "outcome-reveal",
}: OutcomeRevealProps) {
  return (
    <div
      data-testid={testId}
      className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <Wallet size={15} className="text-[#2962ff]" />
        <span
          data-testid="outcome-reveal-flag"
          className="text-[10px] uppercase tracking-widest text-[#2962ff] font-semibold"
        >
          What happened next (educational scenario)
        </span>
      </div>

      <div className="mb-4 rounded-[4px] border border-[#D9DDE2] bg-white p-3">
        <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
          Your decision at the time
        </div>
        <div className="text-lg font-mono font-semibold text-[#1F2933]">
          {decisionLabel(learnerDecision)}
        </div>
        <div className="mt-1 text-xs text-[#667085]">
          Decision point price: ₹
          {decisionPointPrice.toLocaleString("en-IN")}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {outcomes.map((step, index) => (
          <div
            key={step.label}
            data-testid={`outcome-step-${index}`}
            className="rounded-[4px] border border-[#D9DDE2] bg-white p-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-widest text-[#667085]">
                {step.label}
              </span>
              <span
                className={`inline-flex items-center gap-1 font-mono tabular-nums text-sm font-semibold ${
                  step.returnPct >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                }`}
                data-testid={`outcome-return-${index}`}
              >
                <TrendingUp size={13} />
                {step.returnPct >= 0 ? "+" : ""}
                {step.returnPct.toFixed(1)}%
              </span>
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-[#667085]">
              <div className="flex justify-between">
                <dt className="text-[10px] uppercase tracking-widest">Max favourable excursion</dt>
                <dd className="font-mono tabular-nums text-[#26a69a]">
                  +{step.maxFavourableExcursion.toFixed(1)}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[10px] uppercase tracking-widest">Max adverse excursion</dt>
                <dd className="font-mono tabular-nums text-[#ef5350]">
                  {step.maxAdverseExcursion.toFixed(1)}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[10px] uppercase tracking-widest">Target reached</dt>
                <dd className="font-mono tabular-nums">
                  {step.targetReached ? "Yes" : "No"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[10px] uppercase tracking-widest">Invalidation reached</dt>
                <dd className="font-mono tabular-nums">
                  {step.invalidationReached ? "Yes" : "No"}
                </dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}
