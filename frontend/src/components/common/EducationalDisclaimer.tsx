import { Info } from "lucide-react";

interface EducationalDisclaimerProps {
  variant?: "compact" | "inline";
  className?: string;
  testId?: string;
}

const DISCLAIMER_TEXT =
  "TradeLens does not provide stock recommendations or investment advice. " +
  "Signals and analysis are for educational and informational purposes only. " +
  "Conduct your own research and make your own decisions. TradeLens does not guarantee trading or investment outcomes.";

export default function EducationalDisclaimer({
  variant = "compact",
  className = "",
  testId = "educational-disclaimer",
}: EducationalDisclaimerProps) {
  if (variant === "inline") {
    return (
      <p
        data-testid={testId}
        className={`text-[11px] leading-relaxed text-[#667085] ${className}`}
      >
        {DISCLAIMER_TEXT}
      </p>
    );
  }

  return (
    <aside
      data-testid={testId}
      className={`flex items-start gap-2 rounded-[4px] border border-[#D9DDE2] bg-[#F0F1EF] px-3 py-2 ${className}`}
    >
      <Info size={14} className="text-[#667085] shrink-0 mt-0.5" aria-hidden />
      <p className="text-[11px] leading-relaxed text-[#667085]">{DISCLAIMER_TEXT}</p>
    </aside>
  );
}

export const RECOMMENDATION_CONTEXT_MESSAGE =
  "Mentor classifications describe what the available evidence suggests for learning. " +
  "They are not personalized investment advice or trade instructions.";
