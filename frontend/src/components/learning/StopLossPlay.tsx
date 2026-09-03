import { useState } from "react";
import { Check } from "lucide-react";
import type { CaseStudy } from "@/lib/howToUseLessons";
import { revealStopLossDay } from "@/lib/howToUseLessons";

interface StopLossPlayProps {
  caseStudy: CaseStudy;
  /** Called once the learner has made a choice on every day. */
  onComplete: () => void;
  testId?: string;
}

/**
 * Case 08 — "The Stop-Loss Test". The learner already holds a position and
 * reacts day by day. Each day's outcome is revealed only after a choice is
 * made for that day; the case is complete once every day is resolved.
 */
export function StopLossPlay({ caseStudy, onComplete, testId = "stop-loss-play" }: StopLossPlayProps) {
  const [resolvedChoice, setResolvedChoice] = useState<Record<number, string>>({});

  if (caseStudy.interaction.kind !== "stopLoss") return null;
  const days = caseStudy.interaction.days;
  const totalDays = days.length;

  const allResolved = Object.keys(resolvedChoice).length === totalDays;

  function choose(dayIndex: number, choiceId: string) {
    if (allResolved) return;
    setResolvedChoice((prev) => ({ ...prev, [dayIndex]: choiceId }));
    // Only mark the case complete after the final day is resolved.
    if (dayIndex === totalDays - 1) {
      onComplete();
    }
  }

  return (
    <div data-testid={testId} className="flex flex-col gap-4">
      <div data-testid="stop-loss-prompt" className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-3 text-sm font-semibold text-[#1F2933]">
        {caseStudy.interaction.prompt}
      </div>

      {/* Progress through the days */}
      <div className="flex flex-wrap items-center gap-2">
        {days.map((day, index) => {
          const done = resolvedChoice[index] !== undefined;
          return (
            <span
              key={day.day}
              data-testid={`stop-loss-day-marker-${index}`}
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest ${
                done
                  ? "border-[#26a69a]/40 bg-[#26a69a]/[0.06] text-[#26a69a]"
                  : index === days.findIndex((__, i) => resolvedChoice[i] === undefined)
                    ? "border-[#2962ff]/50 bg-[#2962ff]/[0.05] text-[#2962ff]"
                    : "border-[#D9DDE2] bg-white text-[#C5CAD3]"
              }`}
            >
              {done && <Check size={10} />} {day.day}
            </span>
          );
        })}
      </div>

      {days.map((day, index) => {
        const chosenId = resolvedChoice[index];
        const revealed = revealStopLossDay(caseStudy, index, chosenId);
        const isCurrent =
          chosenId === undefined &&
          index === days.findIndex((__, i) => resolvedChoice[i] === undefined);

        if (!isCurrent && !revealed) return null;

        const showChoice = !revealed;
        const blocked = allResolved && !revealed;

        return (
          <div
            key={day.day}
            data-testid={`stop-loss-day-${index}`}
            className="rounded-[4px] border border-[#D9DDE2] bg-white p-4"
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono tabular-nums text-[10px] uppercase tracking-widest text-[#2962ff]">
                {day.day}
              </span>
              <span className="font-mono tabular-nums text-xs text-[#667085]">
                Price ₹{day.currentPrice.toLocaleString("en-IN")}
              </span>
            </div>
            <div className="text-sm font-semibold text-[#1F2933]">{day.headline}</div>
            <p className="mt-1 text-sm leading-relaxed text-[#667085]">{day.detail}</p>

            {showChoice && (
              <div data-testid={`stop-loss-choices-${index}`} className="mt-3 flex flex-col gap-2">
                {day.choices.map((choice) => (
                  <button
                    key={choice.id}
                    type="button"
                    disabled={blocked}
                    onClick={() => choose(index, choice.id)}
                    data-testid={`stop-loss-choice-${index}-${choice.id}`}
                    className={`rounded-[4px] border px-4 py-2.5 text-left text-sm transition-colors disabled:opacity-60 ${
                      chosenId === choice.id
                        ? "border-[#2962ff] bg-[#2962ff]/[0.06] text-[#1F2933]"
                        : "border-[#D9DDE2] bg-white text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/[0.03]"
                    }`}
                  >
                    <span className="font-medium">{choice.label}</span>
                  </button>
                ))}
              </div>
            )}

            {revealed && (
              <div
                data-testid={`stop-loss-resolution-${index}`}
                className="mt-3 rounded-[4px] border border-[#26a69a]/25 bg-[#26a69a]/[0.05] p-3"
              >
                <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#26a69a]">
                  <Check size={12} /> {revealed.day.day} — you chose:{' '}
                  {revealed.chosen.label}
                </div>
                <p className="mt-1 text-sm font-semibold text-[#1F2933]">
                  {revealed.day.resolution.headline}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[#667085]">
                  {revealed.day.resolution.detail}
                </p>
                <div className="mt-2 rounded-[4px] bg-white p-2 text-xs leading-relaxed text-[#1F2933]">
                  <span className="font-semibold text-[#26a69a]">Process: </span>
                  {revealed.day.resolution.processNote}
                </div>
              </div>
            )}

            {!revealed && isCurrent && days[index + 1] && (
              <div className="mt-3 text-[11px] text-[#667085]">
                Make a choice to reveal what happened next.
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
