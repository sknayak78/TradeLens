import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
  compact?: boolean;
  testId?: string;
}

export default function LoadingState({
  label = "Loading…",
  compact,
  testId = "loading-state",
}: LoadingStateProps) {
  return (
    <div
      data-testid={testId}
      className={`flex items-center justify-center gap-2 text-[#787b86] ${
        compact ? "py-6" : "py-10"
      }`}
    >
      <Loader2 size={16} className="animate-spin text-[#2962ff]" />
      <span className="text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}
