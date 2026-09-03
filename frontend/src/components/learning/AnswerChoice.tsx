import type { AnswerOption } from "@/lib/howToUseLessons";

interface AnswerChoiceProps {
  prompt: string;
  options: AnswerOption[];
  selected: string | null;
  onSelect: (id: string) => void;
  disabled?: boolean;
  testId?: string;
}

/**
 * Reusable single-select answer control used across the lessons (and as the
 * basis for confidence selection in the decision lesson).
 */
export function AnswerChoice({
  prompt,
  options,
  selected,
  onSelect,
  disabled = false,
  testId = "answer-choice",
}: AnswerChoiceProps) {
  return (
    <div data-testid={testId}>
      <div
        data-testid="answer-choice-prompt"
        className="mb-3 text-sm font-semibold text-[#1F2933]"
      >
        {prompt}
      </div>
      <div className="flex flex-col gap-2">
        {options.map((option) => {
          const active = selected === option.id;
          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(option.id)}
              data-testid={`answer-option-${option.id}`}
              aria-pressed={active}
              className={`rounded-[4px] border px-4 py-2.5 text-left text-sm transition-colors disabled:opacity-60 ${
                active
                  ? "border-[#2962ff] bg-[#2962ff]/[0.06] text-[#1F2933]"
                  : "border-[#D9DDE2] bg-white text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/[0.03]"
              }`}
            >
              <span className="font-medium">{option.label}</span>
              {option.hint && (
                <span className="mt-0.5 block text-xs text-[#667085]">
                  {option.hint}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
