import { Eye, Hourglass, Rocket, ThumbsUp, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import type { Recommendation, RecommendationAction } from "@/types";
import {
  ACTION_TONE,
  ActionHeadline,
  MetaBadge,
  Tone,
} from "@/components/panels/RecommendationBadges";

const ACTION_ICON: Record<RecommendationAction, ReactNode> = {
  "Strong Buy": <Rocket size={22} />,
  Buy: <ThumbsUp size={22} />,
  Watch: <Eye size={22} />,
  Wait: <Hourglass size={22} />,
  Avoid: <XCircle size={22} />,
};

const STRATEGY_TONE: Record<string, Tone> = {
  "Trend Continuation": "positive",
  Pullback: "info",
  Breakout: "warning",
  Consolidation: "muted",
  "No Entry Yet": "muted",
};

export const CONFIDENCE_HINT =
  "Confidence indicates how strongly the available technical indicators support " +
  "this recommendation. Higher confidence means more independent signals agree " +
  "with the recommendation. It is not the probability that the trade will be profitable.";

/**
 * The action itself — badge, confidence, strategy and data quality.  Lives in
 * the stock header so the page reads stock → price → recommendation.
 */
export default function RecommendationHeadline({
  recommendation,
}: {
  recommendation: Recommendation;
}) {
  const { action, strategy, confidence, dataQuality } = recommendation;
  const tone = ACTION_TONE[action] ?? "muted";

  return (
    <div className="flex flex-col gap-2" data-testid="recommendation-headline">
      <div className="flex items-center gap-3 flex-wrap">
        <ActionHeadline
          action={action}
          icon={ACTION_ICON[action]}
          testId="recommendation-action"
        />
        <div className="flex items-center gap-2 flex-wrap">
          <MetaBadge
            label="Confidence"
            value={`${Math.round(confidence * 100)}%`}
            tone={tone}
            hint={CONFIDENCE_HINT}
            testId="recommendation-confidence"
          />
          <MetaBadge
            label="Strategy"
            value={strategy}
            tone={STRATEGY_TONE[strategy] ?? "muted"}
            testId="recommendation-strategy"
          />
          <MetaBadge
            label="Data Quality"
            value={dataQuality}
            tone={dataQuality === "Complete" ? "muted" : "warning"}
            testId="recommendation-data-quality"
          />
        </div>
      </div>
      <p
        className="text-[11px] text-[#667085] leading-relaxed max-w-2xl"
        data-testid="recommendation-confidence-help"
      >
        Confidence indicates how strongly the available technical indicators
        support this recommendation — not the odds that the trade will be
        profitable.
      </p>
    </div>
  );
}
