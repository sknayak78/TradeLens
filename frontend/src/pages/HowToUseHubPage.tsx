import InfoPageLayout from "@/components/layout/InfoPageLayout";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";
import { LearningProgressProvider } from "@/context/LearningProgressContext";
import { Outlet } from "react-router-dom";

export default function HowToUseHubPage() {
  return (
    <div data-testid="how-to-use-hub" className="min-h-full">
      <InfoPageLayout
        title="TradeLens Academy"
        subtitle="Learn how to evaluate a trading setup by doing — work through 10 realistic cases, then compare your reasoning with the TradeLens Mentor."
        testId="how-to-use-header"
      >
        <LearningProgressProvider>
          <Outlet />
        </LearningProgressProvider>
        <div className="mt-8">
          <EducationalDisclaimer />
        </div>
      </InfoPageLayout>
    </div>
  );
}
