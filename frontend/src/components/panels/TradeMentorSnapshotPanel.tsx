import { ChevronDown } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  hasMentorSnapshot,
  mentorSnapshotRows,
  type MentorSnapshot,
} from "@/lib/tradeMentorSnapshot";

interface TradeMentorSnapshotPanelProps {
  snapshot: MentorSnapshot | null | undefined;
  tradeId: number;
}

export default function TradeMentorSnapshotPanel({
  snapshot,
  tradeId,
}: TradeMentorSnapshotPanelProps) {
  if (!hasMentorSnapshot(snapshot) || !snapshot) {
    return (
      <p
        className="text-[11px] text-[#667085] italic"
        data-testid={`journal-mentor-unavailable-${tradeId}`}
      >
        Mentor snapshot unavailable
      </p>
    );
  }

  const rows = mentorSnapshotRows(snapshot);

  return (
    <Collapsible data-testid={`journal-mentor-snapshot-${tradeId}`}>
      <CollapsibleTrigger className="group flex w-full items-center justify-between rounded-[4px] border border-[#D9DDE2] bg-[#F8F9FA] px-3 py-2 text-left text-[11px] font-medium uppercase tracking-widest text-[#1F2933] hover:bg-[#F0F1EF]">
        <span>TradeLens Mentor — At Entry</span>
        <ChevronDown
          size={14}
          className="text-[#667085] transition-transform group-data-[state=open]:rotate-180"
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-3">
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {rows.map((row) => (
            <div key={row.label}>
              <dt className="text-[10px] uppercase tracking-widest text-[#667085]">
                {row.label}
              </dt>
              <dd
                className="text-sm text-[#1F2933] font-medium"
                data-testid={`journal-mentor-${tradeId}-${row.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
              >
                {row.value}
              </dd>
            </div>
          ))}
        </dl>
        {snapshot.reason ? (
          <div className="mt-3 border-t border-[#D9DDE2]/70 pt-3">
            <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
              Why
            </div>
            <p
              className="text-xs text-[#1F2933] leading-relaxed"
              data-testid={`journal-mentor-${tradeId}-reason`}
            >
              {snapshot.reason}
            </p>
          </div>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}
