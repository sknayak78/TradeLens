import InfoPageLayout from "@/components/layout/InfoPageLayout";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";
import { Outlet } from "react-router-dom";

export default function HowToUseHubPage() {
  return (
    <div data-testid="how-to-use-hub" className="min-h-full">
      <InfoPageLayout
        title="How to Use TradeLens"
        subtitle="Learn what each metric means, how to read the TradeLens Mentor view, and how to study stocks with discipline."
        testId="how-to-use-header"
      >
        <Outlet />
        <div className="mt-8">
          <EducationalDisclaimer />
        </div>
      </InfoPageLayout>
    </div>
  );
}
