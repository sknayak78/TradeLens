import { CheckCircle2, EyeOff, MinusCircle } from "lucide-react";
import {
  caseDecisionLabels,
  type DecisionAction,
  type MentorView,
} from "@/lib/howToUseLessons";
import type { Agreement } from "@/lib/decisions";
import { TRADELENS_MENTOR } from "@/lib/mentorPresentation";

interface MentorRevealProps {
  learnerAction?: DecisionAction;
  mentor: MentorView;
  agreement?: Agreement;
  rationale: string;
  takeaway: string;
  testId?: string;
}

/**
 * Reveals the Mentor view only after the learner has committed their own
 * decision. Shows the learner decision, the Mentor decision, agreement, the
 * rationale and an educational takeaway.
 */
export function MentorReveal({
  learnerAction,
  mentor,
  agreement,
  rationale,
  takeaway,
  testId = "mentor-reveal",
}: MentorRevealProps) {
  const agreementTone =
    agreement === "agree"
      ? { color: "#26a69a", label: "You agreed" }
      : agreement === "partial"
        ? { color: "#f5a623", label: "You partially agreed" }
        : { color: "#ef5350", label: "You differed" };

  return (
    <div
      data-testid={testId}
      className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <EyeOff size={15} className="text-[#2962ff]" />
        <span
          data-testid="mentor-reveal-flag"
          className="text-[10px] uppercase tracking-widest text-[#2962ff] font-semibold"
        >
          MENTOR VIEW · {TRADELENS_MENTOR}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {learnerAction && (
          <div
            data-testid="mentor-reveal-learner"
            className="rounded-[4px] border border-[#D9DDE2] bg-white p-3"
          >
            <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
              Your decision
            </div>
            <div className="text-lg font-mono font-semibold text-[#1F2933]">
              {caseDecisionLabels[learnerAction]}
            </div>
          </div>
        )}
        <div
          data-testid="mentor-reveal-mentor"
          className="rounded-[4px] border border-[#26a69a]/30 bg-[#26a69a]/[0.06] p-3"
        >
          <div className="text-[10px] uppercase tracking-widest text-[#26a69a] mb-1">
            {TRADELENS_MENTOR} decision
          </div>
          <div className="text-lg font-mono font-semibold text-[#1F2933]">
            {mentor.actionLabel ?? mentor.action}
          </div>
        </div>
      </div>

      {agreement && (
        <div
          data-testid="mentor-reveal-agreement"
          className="mt-3 inline-flex items-center gap-1.5 rounded-[4px] border px-3 py-1.5 text-xs font-medium"
          style={{
            color: agreementTone.color,
            borderColor: `${agreementTone.color}40`,
            background: `${agreementTone.color}0f`,
          }}
        >
          {agreement === "agree" ? (
            <CheckCircle2 size={14} />
          ) : (
            <MinusCircle size={14} />
          )}
          {agreementTone.label}
        </div>
      )}

      <div className="mt-4 space-y-3">
        <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-3">
          <div className="mb-1 text-[10px] uppercase tracking-widest text-[#667085]">
            Rationale
          </div>
          <p data-testid="mentor-rationale" className="text-sm leading-relaxed text-[#1F2933]">
            {rationale}
          </p>
          {mentor.reasoning && mentor.reasoning.length > 0 && (
            <ul className="mt-2 space-y-1.5 border-t border-[#D9DDE2] pt-2">
              {mentor.reasoning.map((point, index) => (
                <li
                  key={index}
                  data-testid={`mentor-reasoning-${index}`}
                  className="flex gap-1.5 text-sm leading-relaxed text-[#667085]"
                >
                  <span className="text-[#2962ff]">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[4px] border border-[#26a69a]/25 bg-[#26a69a]/[0.05] p-3">
          <div className="mb-1 text-[10px] uppercase tracking-widest text-[#26a69a]">
            Educational takeaway
          </div>
          <p data-testid="mentor-takeaway" className="text-sm leading-relaxed text-[#1F2933]">
            {takeaway}
          </p>
        </div>
      </div>
    </div>
  );
}
