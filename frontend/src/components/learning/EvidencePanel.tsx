import { ScanSearch } from "lucide-react";
import type { CaseEvidence } from "@/lib/howToUseLessons";

interface EvidencePanelProps {
  evidence: CaseEvidence[];
  testId?: string;
}

const TONE_COLOR: Record<string, string> = {
  bullish: "#26a69a",
  bearish: "#ef5350",
  neutral: "#2962ff",
};

/**
 * The structured technical evidence a case is read against. Revealed only
 * after the learner commits their own call — this is the "understand the
 * reasoning" step of the learning flow.
 */
export function EvidencePanel({ evidence, testId = "evidence-panel" }: EvidencePanelProps) {
  return (
    <div
      data-testid={testId}
      className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <ScanSearch size={15} className="text-[#2962ff]" />
        <span
          data-testid="evidence-panel-flag"
          className="text-[10px] uppercase tracking-widest text-[#2962ff] font-semibold"
        >
          The evidence, read back
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2">
        {evidence.map((row, index) => {
          const color = TONE_COLOR[row.tone ?? "neutral"];
          return (
            <div
              key={`${row.label}-${index}`}
              data-testid={`evidence-row-${index}`}
              className="rounded-[4px] border border-[#D9DDE2] bg-white p-3"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] uppercase tracking-widest text-[#667085]">
                  {row.label}
                </span>
                <span
                  className="font-mono tabular-nums text-xs font-semibold"
                  style={{ color }}
                >
                  {row.value}
                </span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-[#667085]">{row.note}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
