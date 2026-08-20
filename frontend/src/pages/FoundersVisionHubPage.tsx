import InfoPageLayout from "@/components/layout/InfoPageLayout";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";
import FoundersVisionPage from "@/pages/FoundersVisionPage";

export default function FoundersVisionHubPage() {
  return (
    <div data-testid="founders-vision-hub" className="min-h-full">
      <InfoPageLayout
        title="Founder's Vision"
        subtitle="Why TradeLens exists, what we believe, and where we want to take it."
        testId="founders-vision-header"
      >
        <FoundersVisionPage />
        <div className="mt-8">
          <EducationalDisclaimer />
        </div>
      </InfoPageLayout>
    </div>
  );
}
