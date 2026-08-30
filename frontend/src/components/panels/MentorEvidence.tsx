import { CheckCircle2 } from "lucide-react";
import type { HumanizedRule, HumanizedWarning } from "@/lib/mentorPresentation";

export function RuleEvidenceCard({ rule }: { rule: HumanizedRule }) {
  return (
    <li
      className="rounded-[4px] border border-[#D9DDE2] bg-[#F0F1EF] p-3"
      data-testid={`rule-${rule.key}`}
    >
      <div className="flex items-start gap-2">
        <CheckCircle2 size={14} className="text-[#26a69a] shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="text-[13px] font-semibold text-[#1F2933]">{rule.title}</span>
            <span className="text-[11px] font-medium text-[#2962ff]">{rule.status}</span>
          </div>
          {rule.values.length > 0 && (
            <dl className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
              {rule.values.map((row) => (
                <div key={row.label} className="flex justify-between gap-2 text-[11px]">
                  <dt className="text-[#667085]">{row.label}</dt>
                  <dd className="font-mono tabular-nums text-[#1F2933] font-medium">
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          )}
          <p className="text-[12px] text-[#667085] leading-relaxed mt-2">{rule.explanation}</p>
        </div>
      </div>
    </li>
  );
}

export function WarningEvidenceCard({ warning }: { warning: HumanizedWarning }) {
  return (
    <li
      className="rounded-[4px] border border-[#f5a623]/25 bg-[#f5a623]/5 p-3"
      data-testid={`warning-${warning.key}`}
    >
      <div className="text-[13px] font-semibold text-[#1F2933]">{warning.title}</div>
      <p className="text-[12px] text-[#1F2933] mt-1">{warning.summary}</p>
      {warning.values.length > 0 && (
        <dl className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
          {warning.values.map((row) => (
            <div key={row.label} className="flex justify-between gap-2 text-[11px]">
              <dt className="text-[#667085]">{row.label}</dt>
              <dd className="font-mono tabular-nums text-[#1F2933] font-medium">
                {row.value}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-[12px] text-[#667085] leading-relaxed mt-2">{warning.explanation}</p>
    </li>
  );
}
