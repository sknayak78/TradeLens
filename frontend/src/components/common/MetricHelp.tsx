import { useId, useState } from "react";
import { Info } from "lucide-react";
import {
  buildMetricHelp,
  type MetricContext,
  type MetricId,
} from "@/lib/metricEducation";

interface MetricHelpProps {
  metric: MetricId;
  context?: MetricContext;
  /** Optional label shown next to the icon (e.g. column header). */
  label?: string;
  className?: string;
  testId?: string;
}

/**
 * Tap/click-friendly contextual help for technical metrics.
 * Uses a toggle panel so touch devices are supported (not hover-only).
 */
export default function MetricHelp({
  metric,
  context = {},
  label,
  className = "",
  testId,
}: MetricHelpProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const help = buildMetricHelp(metric, context);

  return (
    <span className={`relative inline-flex ${className}`}>
      <button
        type="button"
        data-testid={testId ?? `metric-help-${metric}`}
        className="inline-flex items-center gap-1 text-inherit hover:text-[#2962ff] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2962ff]/40 rounded-sm"
        aria-label={`Learn about ${help.title}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {label && <span>{label}</span>}
        <Info size={12} className="shrink-0 opacity-70" aria-hidden />
      </button>
      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 cursor-default"
            aria-label="Close help"
            onClick={() => setOpen(false)}
          />
          <div
            id={panelId}
            role="dialog"
            className="absolute z-50 bottom-full left-0 mb-2 w-72 max-w-[90vw] rounded-md border border-[#D9DDE2] bg-white p-4 shadow-lg text-[#1F2933] space-y-2"
          >
            <p className="text-sm font-semibold">{help.title}</p>
            <div className="space-y-2 text-xs leading-relaxed text-[#667085]">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-[#2962ff] mb-0.5">
                  What is it?
                </p>
                <p className="text-[#1F2933]">{help.what}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-[#2962ff] mb-0.5">
                  What does the current value mean?
                </p>
                <p className="text-[#1F2933]">{help.meaning}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-[#2962ff] mb-0.5">
                  How should I use it?
                </p>
                <p className="text-[#1F2933]">{help.usage}</p>
              </div>
            </div>
          </div>
        </>
      )}
    </span>
  );
}
