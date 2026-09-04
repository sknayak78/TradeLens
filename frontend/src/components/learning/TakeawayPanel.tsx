import { GraduationCap } from "lucide-react";

interface TakeawayPanelProps {
  takeaway: string;
  learnWhy: string[];
  testId?: string;
}

/**
 * The final "LEARN" step of the case flow: a single memorable takeaway plus
 * the learn-why points. Shown last, after mentor + outcome are revealed.
 */
export function TakeawayPanel({
  takeaway,
  learnWhy,
  testId = "takeaway-panel",
}: TakeawayPanelProps) {
  return (
    <div
      data-testid={testId}
      className="rounded-[4px] border border-[#26a69a]/25 bg-[#26a69a]/[0.05] p-4"
    >
      <div className="mb-2 flex items-center gap-2">
        <GraduationCap size={15} className="text-[#26a69a]" />
        <span
          data-testid="takeaway-flag"
          className="text-[10px] uppercase tracking-widest text-[#26a69a] font-semibold"
        >
          The takeaway
        </span>
      </div>
      <p
        data-testid="takeaway-copy"
        className="text-sm font-semibold text-[#1F2933]"
      >
        {takeaway}
      </p>
      {learnWhy.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-[#26a69a]/20 pt-3 text-sm leading-relaxed text-[#667085]">
          {learnWhy.map((point, index) => (
            <li
              key={index}
              data-testid={`takeaway-point-${index}`}
              className="flex gap-1.5"
            >
              <span className="text-[#26a69a]">•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
