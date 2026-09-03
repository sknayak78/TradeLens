import { useState } from "react";
import { GraduationCap, UserRoundCheck } from "lucide-react";
import type { CaseStudy } from "@/lib/howToUseLessons";
import { buildAssessmentFeedback, type AssessmentSubmission } from "@/lib/howToUseLessons";

interface SelfAssessmentProps {
  caseStudy: CaseStudy;
  onComplete: () => void;
  testId?: string;
}

/**
 * Case 10 — "You Are the Mentor". The learner builds the assessment across six
 * reasoning dimensions, then receives a learning profile. The profile grades
 * the soundness of the reasoning process — never a performance prediction.
 */
export function SelfAssessment({ caseStudy, onComplete, testId = "self-assessment" }: SelfAssessmentProps) {
  const [answers, setAnswers] = useState<AssessmentSubmission>({});
  const [submitted, setSubmitted] = useState(false);

  if (caseStudy.interaction.kind !== "selfAssessment") return null;
  const fields = caseStudy.interaction.fields;

  const allAnswered = fields.every((field) => answers[field.key]);

  function choose(key: string, value: string) {
    if (submitted) return;
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  function submit() {
    if (!allAnswered) return;
    setSubmitted(true);
    onComplete();
  }

  const feedback = submitted ? buildAssessmentFeedback(answers) : null;

  return (
    <div data-testid={testId} className="flex flex-col gap-4">
      <div className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-3 text-sm font-semibold text-[#1F2933]">
        {caseStudy.interaction.prompt}
      </div>

      {!submitted ? (
        <>
          <div className="flex flex-col gap-4">
            {fields.map((field) => {
              const selected = answers[field.key];
              return (
                <div key={field.key} data-testid={`assessment-field-${field.key}`}>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#667085]">
                    {field.label}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {field.options.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => choose(field.key, option.id)}
                        data-testid={`assessment-${field.key}-${option.id}`}
                        aria-pressed={selected === option.id}
                        className={`rounded-[4px] border px-3 py-1.5 text-xs font-medium transition-colors ${
                          selected === option.id
                            ? "bg-[#2962ff] border-[#2962ff] text-white"
                            : "bg-white border-[#D9DDE2] text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5"
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={submit}
              disabled={!allAnswered}
              data-testid="assessment-submit"
              className={`inline-flex items-center gap-1.5 rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                allAnswered
                  ? "bg-[#26a69a] text-white hover:bg-[#26a69a]/85"
                  : "bg-[#E5E7EB] text-[#9CA3AF]"
              }`}
            >
              <UserRoundCheck size={15} /> Reveal my learning profile
            </button>
            {!allAnswered && (
              <span className="text-[11px] text-[#667085]">
                Answer every dimension to reveal your profile.
              </span>
            )}
          </div>
        </>
      ) : (
        <div
          data-testid="assessment-feedback"
          className="rounded-[4px] border border-[#26a69a]/25 bg-[#26a69a]/[0.05] p-4"
        >
          <div className="mb-3 flex items-center gap-2">
            <GraduationCap size={15} className="text-[#26a69a]" />
            <span className="text-[10px] uppercase tracking-widest text-[#26a69a] font-semibold">
              Your learning profile
            </span>
          </div>
          <p className="mb-3 text-xs text-[#667085]">
            This assesses how you reason about a setup. It is not a prediction
            of investment performance or price direction.
          </p>
          <div className="grid grid-cols-1 gap-2">
            {feedback?.dimensions.map((dim) => (
              <div
                key={dim.key}
                data-testid={`assessment-dimension-${dim.key}`}
                className="rounded-[4px] border border-[#D9DDE2] bg-white p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[#1F2933]">{dim.label}</span>
                  <span className="font-mono tabular-nums text-xs text-[#667085]">
                    {Math.round(dim.score * 100)}%
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[#E5E7EB]">
                  <div
                    className="h-full bg-[#26a69a]"
                    style={{ width: `${dim.score * 100}%` }}
                  />
                </div>
                <div className="mt-1 text-[11px] text-[#667085]">{dim.note}</div>
              </div>
            ))}
          </div>
          {feedback && (
            <div
              data-testid="assessment-biggest-improvement"
              className="mt-3 rounded-[4px] border border-[#f5a623]/30 bg-[#fffbea] p-3"
            >
              <div className="mb-1 text-[10px] uppercase tracking-widest text-[#f5a623] font-semibold">
                Your biggest improvement area
              </div>
              <p className="text-sm font-medium text-[#1F2933]">
                {feedback.biggestImprovementArea}
              </p>
              <p className="mt-1 text-xs text-[#667085]">
                {feedback.bigImprovementLabel}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
