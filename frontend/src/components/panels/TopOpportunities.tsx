import PanelCard from "@/components/panels/PanelCard";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import OpportunityCard from "@/components/panels/OpportunityCard";
import OpportunitiesSkeleton from "@/components/panels/OpportunitiesSkeleton";
import { useRankings } from "@/hooks/useMarket";

interface TopOpportunitiesProps {
  onSelect?: (symbol: string) => void;
  activeSymbol?: string;
}

export default function TopOpportunities({
  onSelect,
  activeSymbol,
}: TopOpportunitiesProps) {
  const { data, isLoading, isError, refetch } = useRankings();
  const items = data?.rankings ?? [];

  return (
    <PanelCard
      id="learning-opportunities"
      title="Today's Learning Opportunities"
      subtitle="Curated stocks to study with the TradeLens Mentor."
      testId="card-top-opportunities"
    >
      {isLoading && <OpportunitiesSkeleton />}
      {isError && (
        <ErrorState
          message="Today's Learning Opportunities could not be loaded. The rest of the Dashboard is still available — try again in a moment."
          onRetry={() => refetch()}
          testId="opportunities-error"
        />
      )}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState
          title="No featured stocks right now"
          description="Check back when the scanner surfaces new learning candidates."
          testId="opportunities-empty"
        />
      )}
      {!isLoading && !isError && items.length > 0 && (
        <div
          className="grid grid-cols-1 gap-3 max-h-[min(70vh,720px)] overflow-y-auto pr-1"
          data-testid="opportunities-cards"
        >
          {items.map((ranking) => (
            <OpportunityCard
              key={ranking.symbol}
              ranking={ranking}
              active={activeSymbol === ranking.symbol}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </PanelCard>
  );
}
