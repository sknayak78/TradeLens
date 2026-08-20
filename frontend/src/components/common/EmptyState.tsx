import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  testId?: string;
}

export default function EmptyState({
  title = "Nothing here yet",
  description = "There is no data to display.",
  action,
  testId = "empty-state",
}: EmptyStateProps) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col items-center justify-center text-center py-8 gap-2"
    >
      <span className="w-10 h-10 rounded-md bg-[#D9DDE2]/60 border border-[#D9DDE2] flex items-center justify-center text-[#667085]">
        <Inbox size={18} />
      </span>
      <p className="text-sm text-[#1F2933] font-medium">{title}</p>
      <p className="text-xs text-[#667085] max-w-xs">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
