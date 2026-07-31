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
      <span className="w-10 h-10 rounded-md bg-[#2a2e39]/60 border border-[#2a2e39] flex items-center justify-center text-[#787b86]">
        <Inbox size={18} />
      </span>
      <p className="text-sm text-[#d1d4dc] font-medium">{title}</p>
      <p className="text-xs text-[#787b86] max-w-xs">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
