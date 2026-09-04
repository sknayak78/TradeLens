import { Check, CircleDashed, FlaskConical, Play } from "lucide-react";
import type { CaseStudy } from "@/lib/howToUseLessons";

export type CaseCardState = "completed" | "current" | "not-started";

interface CaseCardProps {
  caseStudy: CaseStudy;
  state: CaseCardState;
  onClick: () => void;
}

/**
 * A single tile on the case-lab landing, showing the case number, title, theme
 * (the embedded concept) and its completion/current state.
 */
export function CaseCard({ caseStudy, state, onClick }: CaseCardProps) {
  const isCompleted = state === "completed";
  const isCurrent = state === "current";

  const stateStyles = isCompleted
    ? "border-[#26a69a]/40 bg-[#26a69a]/[0.05]"
    : isCurrent
      ? "border-[#2962ff]/50 bg-[#2962ff]/[0.04]"
      : "border-[#D9DDE2] bg-white";

  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`case-card-${caseStudy.id}`}
      data-state={state}
      className={`group flex flex-col items-start gap-2 rounded-[4px] border p-4 text-left transition-colors hover:border-[#2962ff]/40 hover:bg-[#F6F7F5] ${stateStyles}`}
    >
      <div className="flex w-full items-center justify-between">
        <span
          data-testid={`case-number-${caseStudy.number}`}
          className="font-mono tabular-nums text-[10px] uppercase tracking-widest text-[#667085]"
        >
          Case {String(caseStudy.number).padStart(2, "0")}
        </span>
        {isCompleted ? (
          <span
            data-testid="case-state-completed"
            className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-widest text-[#26a69a]"
          >
            <Check size={13} /> Completed
          </span>
        ) : isCurrent ? (
          <span
            data-testid="case-state-current"
            className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-widest text-[#2962ff]"
          >
            <Play size={12} /> Current
          </span>
        ) : (
          <CircleDashed
            size={13}
            className="text-[#C5CAD3]"
            aria-label="Not started"
            data-testid="case-state-not-started"
          />
        )}
      </div>

      <div className="text-sm font-semibold text-[#1F2933]">
        {caseStudy.title}
      </div>
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-widest text-[#2962ff]">
        <FlaskConical size={11} /> {caseStudy.theme}
      </div>
      <p className="text-xs leading-relaxed text-[#667085]">
        {caseStudy.summary}
      </p>

      <div className="mt-auto flex items-center gap-1 text-[11px] font-medium text-[#2962ff] opacity-0 transition-opacity group-hover:opacity-100">
        {isCompleted ? "Revisit" : "Open case"} <Play size={12} />
      </div>
    </button>
  );
}
