import WatchlistPanel from "@/components/panels/WatchlistPanel";

export default function WatchlistPage() {
  return (
    <div data-testid="watchlist-page" className="p-4 md:p-6">
      <div className="mb-4">
        <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
          Watchlist
        </h1>
        <p className="text-xs text-[#787b86] mt-1">
          Track your favourite instruments — search from the header to add,
          click × to remove.
        </p>
      </div>
      <WatchlistPanel showRemove />
    </div>
  );
}
