import { DECISION_LABELS, CONFIDENCE_OPTIONS, type Confidence, type DecisionAction } from "@/lib/howToUseLessons";

interface YourCallSelectProps {
  prompt: string;
  action: DecisionAction | null;
  setAction: (a: DecisionAction) => void;
  confidence: Confidence | null;
  setConfidence: (c: Confidence) => void;
  disabled?: boolean;
  testId?: string;
}

const ACTION_OPTIONS: DecisionAction[] = ["BUY", "WATCH", "WAIT", "AVOID"];

/**
 * The "Your Call" control for standard cases: pick a decision action and a
 * confidence level. Nothing is revealed (Mentor/evidence/outcome) until the
 * learner submits.
 */
export function YourCallSelect({
  prompt,
  action,
  setAction,
  confidence,
  setConfidence,
  disabled = false,
  testId = "your-call",
}: YourCallSelectProps) {
  return (
    <div data-testid={testId}>
      <div className="mb-3 text-sm font-semibold text-[#1F2933]">{prompt}</div>

      <div className="flex flex-wrap gap-2">
        {ACTION_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            disabled={disabled}
            onClick={() => setAction(option)}
            data-testid={`your-call-action-${option}`}
            aria-pressed={action === option}
            className={`rounded-[4px] border px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60 ${
              action === option
                ? "bg-[#2962ff] border-[#2962ff] text-white"
                : "bg-white border-[#D9DDE2] text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5"
            }`}
          >
            {DECISION_LABELS[option]}
          </button>
        ))}
      </div>

      <div className="mt-4">
        <div className="mb-2 text-sm font-semibold text-[#1F2933]">
          How confident are you?
        </div>
        <div className="flex gap-2">
          {CONFIDENCE_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              disabled={disabled}
              onClick={() => setConfidence(option)}
              data-testid={`your-call-confidence-${option.toLowerCase()}`}
              aria-pressed={confidence === option}
              className={`rounded-[4px] border px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60 ${
                confidence === option
                  ? "bg-[#2962ff] border-[#2962ff] text-white"
                  : "bg-white border-[#D9DDE2] text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
