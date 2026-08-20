import { useState } from "react";
import { ChevronDown } from "lucide-react";
import TrendBadge from "@/components/panels/TrendBadge";
import { ActionPill, Stars } from "@/components/panels/AnalysisBadges";
import LearnWhyPanel from "@/components/panels/LearnWhyPanel";
import type { Ranking } from "@/types";

interface OpportunityCardProps {
  ranking: Ranking;
  active?: boolean;
  onSelect?: (symbol: string) => void;
}

function cardExplanation(ranking: Ranking): string | null {
  const recommendation = ranking.recommendation;
  // Prefer authoritative Mentor verdict from recommendation payload.
  if (recommendation?.verdict) {
    return recommendation.verdict;
  }
  // Ranking feature text is stock-specific when recommendation is absent.
  if (ranking.reason) {
    return ranking.reason;
  }
  // Last-resort catalogue insight; still tied to this symbol's snapshot.
  if (ranking.insight) {
    return ranking.insight;
  }
  return null;
}

export default function OpportunityCard({
  ranking,
  active = false,
  onSelect,
}: OpportunityCardProps) {
  const [showTechnical, setShowTechnical] = useState(false);
  const action = ranking.recommendation?.action ?? ranking.suggestedAction;
  const explanation = cardExplanation(ranking);

  return (
    <article
      data-testid={`opportunity-card-${ranking.symbol}`}
      onClick={() => onSelect?.(ranking.symbol)}
      className={`rounded-[4px] border bg-[#F6F7F5] p-3 flex flex-col gap-2.5 transition-colors ${
        onSelect ? "cursor-pointer hover:border-[#C5CAD3]" : ""
      } ${
        active
          ? "border-[#2962ff]/50 bg-[#2962ff]/5 ring-1 ring-[#2962ff]/20"
          : "border-[#D9DDE2]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[#1F2933] font-semibold leading-snug truncate">
            {ranking.name}
          </p>
          <p className="text-[11px] text-[#667085] font-mono mt-0.5">
            {ranking.symbol}
          </p>
        </div>
        <div className="font-mono tabular-nums text-sm text-[#1F2933] shrink-0">
          ₹{ranking.price.toLocaleString("en-IN")}
        </div>
      </div>

      <ActionPill
        action={action}
        mentorView
        testId={`card-action-${ranking.symbol}`}
      />

      {explanation && (
        <p
          className="text-[12px] text-[#667085] leading-relaxed"
          data-testid={`card-explanation-${ranking.symbol}`}
        >
          {explanation}
        </p>
      )}

      {ranking.recommendation && (
        <div onClick={(event) => event.stopPropagation()}>
          <LearnWhyPanel
            recommendation={ranking.recommendation}
            symbol={ranking.symbol}
            reason={ranking.reason}
            marketContext={{ price: ranking.price }}
            variant="button"
            toggleLabel="Why This View?"
            testIdPrefix={`card-learn-why-${ranking.symbol}`}
          />
        </div>
      )}

      <div onClick={(event) => event.stopPropagation()}>
        <button
          type="button"
          onClick={() => setShowTechnical((value) => !value)}
          data-testid={`card-technical-toggle-${ranking.symbol}`}
          className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-[#667085] hover:text-[#1F2933] transition-colors"
        >
          Technical details
          <ChevronDown
            size={12}
            className={`transition-transform ${showTechnical ? "rotate-180" : ""}`}
          />
        </button>
        {showTechnical && (
          <div
            className="mt-2 rounded-[3px] border border-[#D9DDE2] bg-[#F0F1EF] p-2.5 flex flex-col gap-2"
            data-testid={`card-technical-${ranking.symbol}`}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <TrendBadge trend={ranking.trend} testId={`card-trend-${ranking.symbol}`} />
              <Stars count={ranking.stars} testId={`card-stars-${ranking.symbol}`} />
              <span className="text-[10px] font-mono text-[#667085]">
                Score {ranking.strengthScore}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-wrap text-[10px] font-mono text-[#667085]">
              <span>#{ranking.rank.toString().padStart(2, "0")}</span>
              <span>·</span>
              <span>{ranking.tradeSetup}</span>
              <span>·</span>
              <span>{ranking.riskLevel} risk</span>
              <span>·</span>
              <span
                className={
                  ranking.changePct >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                }
              >
                {ranking.changePct >= 0 ? "+" : ""}
                {ranking.changePct.toFixed(2)}%
              </span>
            </div>
            {ranking.recommendation?.positives?.[0] && (
              <p className="text-[11px] text-[#667085] leading-relaxed border-t border-[#D9DDE2] pt-2">
                {ranking.recommendation.positives[0]}
              </p>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
