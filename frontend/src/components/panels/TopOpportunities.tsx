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
  const discovery = data?.sourceMode === "discovery";
  const funnelMetrics = data
    ? ([
        ["Universe", data.universeCount],
        ["Eligible", data.eligibleCount],
        ["Scanned", data.scannedCount],
        ["Candidates", data.candidateCount],
        ["Ranked", data.rankedCount],
        ["Deep limit", data.deepAnalysisLimit],
        ["Analysed", data.analysedCount],
        ["Final", data.finalOpportunityCount],
      ].filter(([, value]) => value != null) as [string, number][])
    : [];

  return (
    <PanelCard
      id="learning-opportunities"
      title="Today's Learning Opportunities"
      subtitle={
        discovery
          ? "Discovered from the broader NSE market"
          : "Curated fallback to study with the TradeLens Mentor."
      }
      testId="card-top-opportunities"
    >
      {funnelMetrics.length > 0 && (
        <div
          className="mb-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-mono tabular-nums text-[#667085]"
          data-testid="opportunities-funnel"
          aria-label={discovery ? "Broad-market discovery funnel" : "Curated fallback funnel"}
        >
          {funnelMetrics.map(([label, value]) => (
            <span key={label}>
              {label} {value.toLocaleString("en-IN")}
            </span>
          ))}
        </div>
      )}
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
