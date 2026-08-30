import { Skeleton } from "@/components/ui/skeleton";

/** Skeleton placeholders while Today's Learning Opportunities loads. */
export default function OpportunitiesSkeleton({
  testId = "opportunities-skeleton",
}: {
  testId?: string;
}) {
  return (
    <div className="grid grid-cols-1 gap-3" data-testid={testId}>
      {[0, 1, 2].map((key) => (
        <div
          key={key}
          className="rounded-[4px] border border-[#D9DDE2] bg-[#F6F7F5] p-3 space-y-2.5"
        >
          <div className="flex justify-between gap-3">
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-4 w-3/5 bg-[#D9DDE2]" />
              <Skeleton className="h-3 w-1/4 bg-[#D9DDE2]" />
            </div>
            <Skeleton className="h-4 w-16 bg-[#D9DDE2]" />
          </div>
          <Skeleton className="h-10 w-36 bg-[#D9DDE2]" />
          <Skeleton className="h-3 w-full bg-[#D9DDE2]" />
          <Skeleton className="h-3 w-4/5 bg-[#D9DDE2]" />
        </div>
      ))}
    </div>
  );
}
