import { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Compass,
  GraduationCap,
  Info,
  Lightbulb,
} from "lucide-react";
import type { Recommendation } from "@/types";
import type { MarketContext } from "@/lib/mentorPresentation";
import {
  humanizeRule,
  humanizeWarning,
  TRADELENS_MENTOR,
} from "@/lib/mentorPresentation";
import { RuleEvidenceCard, WarningEvidenceCard } from "@/components/panels/MentorEvidence";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import EducationalDisclaimer, {
  RECOMMENDATION_CONTEXT_MESSAGE,
} from "@/components/common/EducationalDisclaimer";
import { ReasonList } from "@/components/panels/RecommendationBadges";

interface LearnWhyPanelProps {
  recommendation: Recommendation;
  symbol: string;
  reason?: string;
  marketContext?: MarketContext;
  variant?: "embedded" | "button";
  toggleLabel?: string;
  testIdPrefix?: string;
}

function normalise(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function LearnWhyContent({
  recommendation,
  symbol,
  reason,
  marketContext = {},
  testIdPrefix = "learn-why",
}: Omit<LearnWhyPanelProps, "variant">) {
  const {
    action,
    verdict,
    summary,
    positives,
    why,
    risks,
    beginnerTip,
    nextTrigger,
    idealFor,
    rulesMatched,
    warnings,
    rationale,
    levels,
  } = recommendation;

  const shown = new Set(positives.map(normalise));
  const keyReasons = why.filter((item) => !shown.has(normalise(item)));

  return (
    <div className="flex flex-col gap-3" data-testid={`${testIdPrefix}-content`}>
      <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4">
        <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
          {TRADELENS_MENTOR} view · {symbol}
        </div>
        <p className="text-[#1F2933] text-base font-semibold leading-snug">{verdict}</p>
        <p className="text-[13px] text-[#1F2933] leading-relaxed mt-2">{summary}</p>
        {reason && (
          <p className="text-[12px] text-[#667085] border-t border-[#D9DDE2] pt-2 mt-3">
            Featured context: {reason}
          </p>
        )}
      </div>

      <Accordion
        type="multiple"
        defaultValue={["overview", "evidence"]}
        className="rounded-[4px] border border-[#D9DDE2] bg-white px-3"
      >
        <AccordionItem value="overview" className="border-[#D9DDE2]">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Info size={12} />
              What the system sees
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-3 text-[13px] text-[#1F2933] leading-relaxed">
            <p>
              TradeLens classified this stock as <strong className="text-[#1F2933]">{action}</strong>{" "}
              based on the technical evidence available in the catalogue. {TRADELENS_MENTOR} reads trend,
              momentum, structure, and risk context — then explains the result in plain language.
            </p>
            {rationale && <p className="mt-2">{rationale}</p>}
            {rulesMatched.length > 0 && (
              <ul className="mt-3 space-y-2">
                {rulesMatched.map((rule) => (
                  <RuleEvidenceCard
                    key={rule}
                    rule={humanizeRule(rule, marketContext)}
                  />
                ))}
              </ul>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="evidence" className="border-[#D9DDE2]">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Compass size={12} />
              Supporting evidence
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <div className="grid grid-cols-1 gap-2">
              <ReasonList
                title="Strengths"
                items={positives}
                icon={<CheckCircle2 size={12} />}
                tone="positive"
                testId={`${testIdPrefix}-positives`}
              />
              <ReasonList
                title="Key reasons"
                items={keyReasons}
                icon={<Compass size={12} />}
                tone="info"
                testId={`${testIdPrefix}-why`}
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="gaps" className="border-[#D9DDE2]">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <AlertTriangle size={12} />
              What is missing / risk
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <ReasonList
              title="Risks"
              items={risks}
              icon={<AlertTriangle size={12} />}
              tone="negative"
              testId={`${testIdPrefix}-risks`}
            />
            {warnings.length > 0 && (
              <div className="mt-2 rounded-[4px] border border-[#f5a623]/25 bg-[#f5a623]/5 p-3">
                <div className="text-[10px] uppercase tracking-widest text-[#f5a623] mb-2">
                  Warnings
                </div>
                <ul className="space-y-2">
                  {warnings.map((warning) => (
                    <WarningEvidenceCard
                      key={warning}
                      warning={humanizeWarning(warning, marketContext, levels)}
                    />
                  ))}
                </ul>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="lesson" className="border-0">
          <AccordionTrigger className="text-[11px] uppercase tracking-widest text-[#667085] hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <GraduationCap size={12} />
              {TRADELENS_MENTOR} lesson
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <p className="text-[13px] text-[#1F2933] leading-relaxed">{beginnerTip}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
              <div className="rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] px-3 py-2">
                <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
                  Watch next
                </div>
                <div className="text-[13px] text-[#1F2933]">{nextTrigger}</div>
              </div>
              <div className="rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] px-3 py-2">
                <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
                  Ideal for
                </div>
                <div className="text-[13px] text-[#1F2933]">{idealFor}</div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <EducationalDisclaimer variant="inline" testId={`${testIdPrefix}-disclaimer`} />
      <p className="text-[11px] text-[#667085] leading-relaxed">
        {RECOMMENDATION_CONTEXT_MESSAGE}
      </p>
    </div>
  );
}

export default function LearnWhyPanel({
  recommendation,
  symbol,
  reason,
  marketContext,
  variant = "embedded",
  toggleLabel = "Learn Why",
  testIdPrefix = "learn-why",
}: LearnWhyPanelProps) {
  const [open, setOpen] = useState(variant === "embedded");

  if (variant === "button") {
    return (
      <div data-testid={`${testIdPrefix}-wrapper`}>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          data-testid={`${testIdPrefix}-toggle`}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[4px] border border-[#2962ff]/30 bg-[#2962ff]/10 text-[#2962ff] text-[11px] font-semibold uppercase tracking-wider hover:bg-[#2962ff]/15 transition-colors"
        >
          <Lightbulb size={13} />
          {toggleLabel}
          <ChevronDown
            size={13}
            className={`transition-transform ${open ? "rotate-180" : ""}`}
          />
        </button>
        {open && (
          <div className="mt-3">
            <LearnWhyContent
              recommendation={recommendation}
              symbol={symbol}
              reason={reason}
              marketContext={marketContext}
              testIdPrefix={testIdPrefix}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded-[4px] border border-[#2962ff]/20 bg-[#2962ff]/[0.04] p-4"
      data-testid={`${testIdPrefix}-panel`}
    >
      <div className="flex items-center gap-2 mb-3">
        <BookOpen size={14} className="text-[#2962ff]" />
        <span className="text-[11px] uppercase tracking-widest text-[#2962ff] font-semibold">
          Learn Why
        </span>
      </div>
      <LearnWhyContent
        recommendation={recommendation}
        symbol={symbol}
        reason={reason}
        marketContext={marketContext}
        testIdPrefix={testIdPrefix}
      />
    </div>
  );
}
