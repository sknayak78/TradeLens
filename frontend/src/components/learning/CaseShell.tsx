import { ArrowLeft, ArrowRight, Check, Compass, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import { SituationChart } from "@/components/learning/SituationChart";
import type { CaseStudy } from "@/lib/howToUseLessons";

interface CaseShellProps {
  caseStudy: CaseStudy;
  children: ReactNode;
  onBackToList: () => void;
  onPrevious?: () => void;
  onContinue?: () => void;
  onRestart?: () => void;
  continueLabel?: string;
  continueDisabled?: boolean;
  completed?: boolean;
  previousNumber?: number;
  nextNumber?: number;
}

/**
 * Shared shell that frames the case situation + chart and the reveal pipeline
 * body. The shell renders the OBSERVE/ANALYSE portion (situation + chart) and
 * the navigation; it never reveals Mentor/evidence/outcome content itself —
 * the caller decides what to reveal and when.
 */
export function CaseShell({
  caseStudy,
  children,
  onBackToList,
  onPrevious,
  onContinue,
  onRestart,
  continueLabel = "Continue",
  continueDisabled = false,
  completed = false,
  previousNumber,
  nextNumber,
}: CaseShellProps) {
  return (
    <div data-testid={`case-shell-${caseStudy.id}`}>
      {/* Header */}
      <div className="mb-4">
        <button
          type="button"
          onClick={onBackToList}
          data-testid="case-back-to-list"
          className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-[#2962ff] hover:underline"
        >
          <ArrowLeft size={13} /> All cases
        </button>
        <div className="flex items-center gap-2">
          <span className="font-mono tabular-nums text-[10px] uppercase tracking-widest text-[#2962ff]">
            Case {String(caseStudy.number).padStart(2, "0")}
          </span>
          <span className="flex items-center gap-1 rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] px-2 py-0.5 text-[10px] uppercase tracking-widest text-[#667085]">
            <Compass size={10} /> {caseStudy.theme}
          </span>
          {completed && (
            <span
              data-testid="case-completed-flag"
              className="flex items-center gap-1 rounded-[3px] border border-[#26a69a]/30 bg-[#26a69a]/10 px-2 py-0.5 text-[10px] uppercase tracking-widest text-[#26a69a]"
            >
              <Check size={11} /> Completed
            </span>
          )}
        </div>
        <h2 className="mt-1 text-lg font-semibold text-[#1F2933] tracking-tight">
          {caseStudy.title}
        </h2>
        <p className="mt-1 text-sm text-[#667085] max-w-3xl">{caseStudy.summary}</p>
      </div>

      {/* Situation */}
      <div
        data-testid="case-situation"
        className="mb-4 rounded-[4px] border border-[#D9DDE2] bg-white p-4"
      >
        <div className="mb-1 text-[10px] uppercase tracking-widest text-[#667085]">
          The situation
        </div>
        <p className="text-sm leading-relaxed text-[#1F2933]">{caseStudy.situation}</p>
        {caseStudy.chart && (
          <div className="mt-3">
            <SituationChart chart={caseStudy.chart} />
          </div>
        )}
      </div>

      {/* Reveal pipeline body */}
      <div className="flex flex-col gap-4">{children}</div>

      {/* Navigation */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#D9DDE2] pt-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onPrevious}
            disabled={!onPrevious}
            data-testid="case-previous"
            className={`inline-flex items-center gap-1.5 rounded px-3 py-2 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              onPrevious
                ? "border border-[#D9DDE2] bg-white text-[#1F2933] hover:bg-[#F0F1EF]"
                : ""
            }`}
          >
            <ArrowLeft size={14} /> Previous
            {previousNumber !== undefined && (
              <span className="text-xs text-[#667085]">({previousNumber})</span>
            )}
          </button>
          {onRestart && (
            <button
              type="button"
              onClick={onRestart}
              data-testid="case-restart"
              className="inline-flex items-center gap-1.5 rounded border border-[#D9DDE2] bg-white px-3 py-2 text-sm font-medium text-[#1F2933] hover:bg-[#F0F1EF] transition-colors"
            >
              <RotateCcw size={13} /> Restart
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={onContinue}
          disabled={continueDisabled}
          data-testid="case-continue"
          className={`inline-flex items-center gap-1.5 rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            continueDisabled
              ? "bg-[#E5E7EB] text-[#9CA3AF]"
              : "bg-[#2962ff] text-white hover:bg-[#2962ff]/85"
          }`}
        >
          {continueLabel} <ArrowRight size={14} />
          {nextNumber !== undefined && (
            <span className="text-xs opacity-80">({nextNumber})</span>
          )}
        </button>
      </div>
    </div>
  );
}
