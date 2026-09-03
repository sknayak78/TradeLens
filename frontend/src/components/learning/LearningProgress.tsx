import { BookOpenCheck, RotateCcw } from "lucide-react";

interface LearningProgressProps {
  completedCount: number;
  totalLessons: number;
  onReset?: () => void;
}

/**
 * Progress indicator for the "Learn TradeLens by Doing" journey: shows a
 * count ("X / 10 completed") and a visual progress bar plus a reset action.
 */
export function LearningProgress({
  completedCount,
  totalLessons,
  onReset,
}: LearningProgressProps) {
  const pct =
    totalLessons === 0 ? 0 : Math.round((completedCount / totalLessons) * 100);

  return (
    <div
      data-testid="learning-progress"
      className="rounded-[4px] border border-[#D9DDE2] bg-white p-4"
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <BookOpenCheck size={16} className="text-[#2962ff]" />
          <span
            data-testid="learning-progress-count"
            className="font-mono tabular-nums text-sm font-semibold text-[#1F2933]"
          >
            {completedCount} / {totalLessons} cases completed
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            data-testid="learning-progress-pct"
            className="font-mono tabular-nums text-[11px] text-[#667085]"
          >
            {pct}%
          </span>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              data-testid="learning-progress-reset"
              disabled={completedCount === 0}
              className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-[#667085] border border-[#D9DDE2] bg-white hover:bg-[#F0F1EF] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <RotateCcw size={12} /> Reset
            </button>
          )}
        </div>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#E5E7EB]">
        <div
          data-testid="learning-progress-bar"
          className="h-full bg-gradient-to-r from-[#2962ff] to-[#26a69a] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
